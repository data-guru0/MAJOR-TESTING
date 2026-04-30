# AI Code Reviewer — Complete Production Setup Documentation

This document covers everything from zero to a fully running production system.
All commands are for Windows Command Prompt (CMD). Open CMD by pressing Win + R, type `cmd`, press Enter.
Follow every step in exact order. Do not skip anything.

---

## Progress Tracker

| Phase | Status |
|---|---|
| Phase 1 — Accounts | DONE |
| Phase 2 — Install Tools | DONE |
| Phase 3 — AWS Account Setup | DONE |
| Phase 4 — GitHub Repository Setup | DONE |
| Phase 5 — Create GitHub App | DONE |
| Phase 6 — LangFuse Setup | DONE |
| Phase 7 — OpenAI API Key | DONE |
| Phase 8 — Provision AWS Infrastructure | DONE |
| Phase 9 — Configure GitHub Secrets | DONE |
| Phase 10 — First Deployment via GitHub Actions | DONE |
| Phase 11 — Connect kubectl to EKS | DONE |
| Phase 12 — Apply Kubernetes Manifests | DONE |
| Phase 13 — Set Up Grafana and Prometheus | DONE |
| Phase 14 — Set Up LangFuse Tracing | DONE |
| Phase 15 — Update GitHub App Webhook URL | DONE |
| Phase 16 — End-to-End Test | DONE |

---

## Table of Contents

1. [What This System Does](#1-what-this-system-does)
2. [Architecture Overview](#2-architecture-overview)
3. [Your Machine Requirements](#3-your-machine-requirements)
4. [Phase 1 — Accounts You Need](#4-phase-1--accounts-you-need)
5. [Phase 2 — Install Tools on Your Windows Machine](#5-phase-2--install-tools-on-your-windows-machine)
6. [Phase 3 — AWS Account Setup](#6-phase-3--aws-account-setup)
7. [Phase 4 — GitHub Repository Setup](#7-phase-4--github-repository-setup)
8. [Phase 5 — Create GitHub App](#8-phase-5--create-github-app)
9. [Phase 6 — LangFuse Setup](#9-phase-6--langfuse-setup)
10. [Phase 7 — OpenAI API Key](#10-phase-7--openai-api-key)
11. [Phase 8 — Provision AWS Infrastructure with Terraform](#11-phase-8--provision-aws-infrastructure-with-terraform)
12. [Phase 9 — Configure GitHub Secrets](#12-phase-9--configure-github-secrets)
13. [Phase 10 — First Deployment via GitHub Actions](#13-phase-10--first-deployment-via-github-actions)
14. [Phase 11 — Connect kubectl to EKS](#14-phase-11--connect-kubectl-to-eks)
15. [Phase 12 — Apply Kubernetes Manifests](#15-phase-12--apply-kubernetes-manifests)
16. [Phase 13 — Set Up Grafana and Prometheus](#16-phase-13--set-up-grafana-and-prometheus)
17. [Phase 14 — Set Up LangFuse Tracing](#17-phase-14--set-up-langfuse-tracing)
18. [Phase 15 — Update GitHub App Webhook URL](#18-phase-15--update-github-app-webhook-url)
19. [Phase 16 — End-to-End Test](#19-phase-16--end-to-end-test)
20. [Accessing All Dashboards and UIs](#20-accessing-all-dashboards-and-uis)
21. [How the Weekly Evaluation Works](#21-how-the-weekly-evaluation-works)
22. [How to Check If Everything is Running](#22-how-to-check-if-everything-is-running)
23. [Troubleshooting](#23-troubleshooting)
24. [Cost Estimate](#24-cost-estimate)
25. [Teardown — Complete Cleanup](#25-teardown--complete-cleanup)

---

## 1. What This System Does

When a developer opens a Pull Request on any GitHub repository where your GitHub App is installed:

1. GitHub sends a webhook event to your system
2. The gateway service verifies the request is genuinely from GitHub
3. The webhook service stores the PR in your database and queues an analysis job
4. The orchestrator service fetches the actual code diff from GitHub
5. Four AI agents run in parallel and analyze the code for:
   - Static analysis issues (complexity, unused variables, bad naming)
   - Security vulnerabilities (OWASP Top 10, hardcoded secrets, SQL injection)
   - Style issues (formatting, readability)
   - Architecture issues (separation of concerns, missing error handling)
6. The reviewer service posts the findings as inline comments directly on the GitHub PR
7. When the PR is merged, the learner service stores the patterns to improve future reviews

---

## 2. Architecture Overview

```
Internet
    |
    v
AWS Load Balancer (public IP)
    |
    v
gateway service (port 8000)      <- verifies GitHub HMAC signature
    |
    v
webhook service (port 8001)      <- parses event, writes to RDS PostgreSQL
    |
    v
Celery Worker (Redis broker)     <- runs background tasks
    |
    v
orchestrator service (port 8002) <- calls GitHub API, runs LangGraph AI agents
    |
    +-- static analysis agent  -+
    +-- security agent          +-- run in parallel via LangGraph
    +-- style agent             |
    +-- architecture agent     -+
    |
    v
reviewer service (port 8003)    <- posts comments to GitHub PR
    |
    v
[on merge] learner (port 8004)  <- stores patterns in PostgreSQL

Infrastructure:
- EKS (Kubernetes)      runs all services
- RDS PostgreSQL 15     stores PRs, findings, patterns
- ElastiCache Redis     Celery task queue
- ECR                   stores Docker images
- S3                    report storage
- LangFuse              AI call tracing and observability
- Prometheus + Grafana  metrics and dashboards
```

---

## 3. Your Machine Requirements

You run deployment commands from your local Windows machine. The actual application runs entirely on AWS — your machine only needs to run CLI tools.

**What your machine needs:**
- Windows 10 or Windows 11
- 4 GB RAM minimum (8 GB recommended)
- 5 GB free disk space
- Stable internet connection

**Your machine never builds Docker images or runs the application.**
GitHub Actions (running on GitHub's servers) handles all that.
Your CMD terminal is only used to run Terraform, kubectl, AWS CLI, and Git commands.

**What runs on AWS (not on your machine):**
- All 5 services run as pods on EKS nodes (t3.medium — 2 vCPU, 4 GB RAM each, 2 nodes)
- PostgreSQL runs on RDS
- Redis runs on ElastiCache

---

## 4. Phase 1 — Accounts You Need

Create all these accounts before doing anything else.

### 4.1 AWS Account

1. Go to https://aws.amazon.com
2. Click "Create an AWS Account"
3. Enter your email, a password, and an account name
4. Enter your credit card (you will be charged for what you use — see the cost estimate at the end)
5. Complete phone verification
6. Choose "Basic support" (free)
7. Log in to the AWS Console at https://console.aws.amazon.com

### 4.2 GitHub Account

1. Go to https://github.com
2. Sign up if you do not have an account
3. Verify your email address

### 4.3 OpenAI Account

1. Go to https://platform.openai.com
2. Sign up with your email
3. Go to Billing and add a payment method
4. Add at least $10 of credits — this is needed to call GPT-4o-mini
5. Go to Billing → Usage limits and set a monthly limit of $20 to avoid surprises

### 4.4 LangFuse Account

LangFuse records every single OpenAI API call your system makes. You can see what prompt was sent, what came back, how many tokens were used, and what it cost. It is free.

1. Go to https://langfuse.com
2. Click "Get Started Free"
3. Sign up with GitHub or email
4. After signing in, create a new project — name it `ai-code-reviewer`
5. Go to Settings in the left sidebar
6. Click "API Keys"
7. Click "Create new API key"
8. Copy and save both keys:
   - Public Key (starts with `pk-lf-`) — you will need this later
   - Secret Key (starts with `sk-lf-`) — you will need this later

---

## 5. Phase 2 — Install Tools on Your Windows Machine

Open CMD as Administrator for all install steps. To open CMD as Administrator:
Press Win, type `cmd`, right-click "Command Prompt", click "Run as administrator".

### 5.1 Install AWS CLI

1. Open your browser and go to:
   https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2-windows.html
2. Click the link to download the Windows installer (`AWSCLIV2.msi`)
3. Double-click the downloaded file and run the installer
4. Keep all default settings and click through to finish
5. Close and reopen CMD
6. Run this to verify:
   ```
   aws --version
   ```
   You should see: `aws-cli/2.x.x Python/3.x.x Windows/...`

### 5.2 Install Terraform

1. Go to https://developer.hashicorp.com/terraform/install
2. Under Windows, click "AMD64" to download the zip file
3. Open the downloaded zip file
4. Extract `terraform.exe` from the zip
5. Move `terraform.exe` to `C:\Windows\System32\`
   (This makes the `terraform` command available from any folder in CMD)
6. Close and reopen CMD
7. Run this to verify:
   ```
   terraform --version
   ```
   You should see: `Terraform v1.x.x`

### 5.3 Install kubectl

1. Go to https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/
2. Download the latest `kubectl.exe` binary (there is a direct download link on that page)
3. Move `kubectl.exe` to `C:\Windows\System32\`
4. Close and reopen CMD
5. Run this to verify:
   ```
   kubectl version --client
   ```
   You should see a version number printed

### 5.4 Install Git

1. Go to https://git-scm.com/download/win
2. Download the installer (64-bit)
3. Run the installer — keep all default settings
4. Click through to finish
5. Close and reopen CMD
6. Run this to verify:
   ```
   git --version
   ```
   You should see: `git version 2.x.x.windows.x`

### 5.5 Install Helm

Helm is needed to install Prometheus and Grafana on your Kubernetes cluster.

1. Go to https://helm.sh/docs/intro/install/
2. Under "From the Binary Releases" section, click the link for Windows
3. Download the zip for windows-amd64
4. Extract `helm.exe` from the zip
5. Move `helm.exe` to `C:\Windows\System32\`
6. Close and reopen CMD
7. Run this to verify:
   ```
   helm version
   ```

### 5.6 Verify all tools are installed

Open a fresh CMD window and run all five commands. All must show a version number:

```
aws --version
terraform --version
kubectl version --client
git --version
helm version
```

If any of these fails, go back to that tool's step and reinstall it.

---

## 6. Phase 3 — AWS Account Setup

### 6.1 Create an IAM User for CLI access

1. Go to https://console.aws.amazon.com
2. In the search bar at the top type `IAM` and click on IAM
3. In the left sidebar click "Users"
4. Click "Create user"
5. Username: `ai-reviewer-deployer`
6. Click Next
7. Select "Attach policies directly"
8. In the search box type `AdministratorAccess`
9. Check the box next to `AdministratorAccess`
10. Click Next
11. Click "Create user"
12. Click on the user `ai-reviewer-deployer` that you just created
13. Click the "Security credentials" tab
14. Scroll down to "Access keys" and click "Create access key"
15. Select "Command Line Interface (CLI)"
16. Check the confirmation checkbox at the bottom
17. Click Next, then "Create access key"
18. You will now see the Access Key ID and Secret Access Key
19. **IMPORTANT: Copy both values right now into a Notepad file.**
    Once you close this page, you can never see the Secret Access Key again.

### 6.2 Configure AWS CLI with your credentials

Open CMD and run:

```
aws configure
```

It will ask four questions. Answer them exactly like this:

```
AWS Access Key ID [None]: paste your Access Key ID here and press Enter
AWS Secret Access Key [None]: paste your Secret Access Key here and press Enter
Default region name [None]: us-east-1
Default output format [None]: json
```

Now verify it works:

```
aws sts get-caller-identity
```

You should see a response with your account ID and user ARN. If you see an error, your credentials are wrong — go back to step 6.1 and create new access keys.

### 6.3 Save your AWS Account ID

Run this command:

```
aws sts get-caller-identity --query Account --output text
```

This prints a 12-digit number like `123456789012`. Save this number — it is your `AWS_ACCOUNT_ID`. You will need it in later steps.

### 6.4 Create OIDC Identity Provider for GitHub Actions

This allows GitHub Actions to deploy to AWS without storing long-lived AWS keys in GitHub. It is the secure, recommended way.

1. Go to AWS Console → IAM
2. In the left sidebar click "Identity providers"
3. Click "Add provider"
4. Provider type: select "OpenID Connect"
5. Provider URL: `https://token.actions.githubusercontent.com`
6. Click "Get thumbprint" — it will auto-fill
7. Audience: `sts.amazonaws.com`
8. Click "Add provider"

### 6.5 Create IAM Role for GitHub Actions

1. Go to IAM → Roles → "Create role"
2. Trusted entity type: select "Web identity"
3. Identity provider: select `token.actions.githubusercontent.com`
4. Audience: select `sts.amazonaws.com`
5. Click Next
6. You need to add a condition. Scroll down and click "Add condition":
   - Condition operator: `StringLike`
   - Condition key: `token.actions.githubusercontent.com:sub`
   - Value: `repo:YOUR_GITHUB_USERNAME/ai-code-reviewer:*`
   (Replace YOUR_GITHUB_USERNAME with your actual GitHub username — for example `repo:johnsmith/ai-code-reviewer:*`)
7. Click Next
8. In the search box type `AdministratorAccess` and check it
9. Click Next
10. Role name: `github-actions-ai-reviewer`
11. Click "Create role"
12. Click on the role `github-actions-ai-reviewer` that you just created
13. Copy the Role ARN at the top — it looks like:
    `arn:aws:iam::123456789012:role/github-actions-ai-reviewer`
14. Save this. It is your `AWS_ROLE_ARN`.

---

## 7. Phase 4 — GitHub Repository Setup

### 7.1 Create the repository on GitHub

1. Go to https://github.com
2. Click the "+" icon in the top right → "New repository"
3. Repository name: `ai-code-reviewer`
4. Visibility: Private
5. Do NOT check "Add a README file"
6. Click "Create repository"

### 7.2 Create a Personal Access Token for pushing code

1. Go to GitHub → click your profile picture → Settings
2. Scroll all the way down in the left sidebar → "Developer settings"
3. Click "Personal access tokens" → "Tokens (classic)"
4. Click "Generate new token" → "Generate new token (classic)"
5. Note (name): `ai-code-reviewer-push`
6. Expiration: 90 days
7. Check these scopes: `repo` and `workflow`
8. Click "Generate token"
9. Copy the token — it starts with `ghp_...`
10. Save it. You will use this as your password when Git asks.

### 7.3 Push the project code to GitHub

Open CMD and run these commands one by one:

```
cd "D:\MAJOR PROJECT KRISH SIR\ai-code-reviewer"
```

```
git init
```

```
git add .
```

```
git commit -m "initial: full project setup"
```

```
git branch -M main
```

```
git remote add origin https://github.com/YOUR_USERNAME/ai-code-reviewer.git
```

```
git push -u origin main
```

When CMD asks for your GitHub username, enter your GitHub username.
When it asks for your password, paste the Personal Access Token you created in step 7.2 (not your GitHub account password).

After this completes, go to https://github.com/YOUR_USERNAME/ai-code-reviewer and you should see all the project files there.

---

## 8. Phase 5 — Create GitHub App

The GitHub App is the identity your bot uses to read PR diffs and post review comments on GitHub.

### 8.1 Open the GitHub App creation page

1. Go to GitHub → click your profile picture → Settings
2. Scroll down in the left sidebar → "Developer settings"
3. Click "GitHub Apps"
4. Click "New GitHub App"

### 8.2 Fill in the app details

Fill in each field:

- **GitHub App name:** `ai-code-reviewer-bot`
  (This name must be globally unique across all of GitHub. If it is taken, add numbers like `ai-code-reviewer-bot-2024`)
- **Homepage URL:** `https://github.com/YOUR_USERNAME/ai-code-reviewer`
- **Webhook** section — make sure "Active" is checked
- **Webhook URL:** `https://placeholder.com`
  (You will replace this with the real URL in Phase 15 after deployment)
- **Webhook secret:** Type a long random string. Example: `myWebhookSecret_abc123XYZ789`
  Write this down — it is your `GITHUB_WEBHOOK_SECRET`. You need it later.

### 8.3 Set Repository Permissions

Scroll down to "Repository permissions". Change these two:

- **Contents:** Read-only
- **Pull requests:** Read and write

Leave everything else as "No access".

### 8.4 Subscribe to events

Scroll down to "Subscribe to events". Check this box:

- Pull request

### 8.5 Where can this app be installed

Select "Any account" so you can install it on any of your repositories.

### 8.6 Create the app and save credentials

1. Click "Create GitHub App" at the bottom
2. You are now on the app's settings page
3. Look for **App ID** near the top — it is a number like `12345678`
   Save this. It is your `GITHUB_APP_ID`.
4. Scroll down to the "Private keys" section
5. Click "Generate a private key"
6. A `.pem` file will automatically download to your Downloads folder
7. Open that `.pem` file with Notepad:
   - Go to your Downloads folder
   - Right-click the `.pem` file → Open with → Notepad
8. The file contains text starting with `-----BEGIN RSA PRIVATE KEY-----`
9. Press Ctrl+A to select all, then Ctrl+C to copy
10. Save this somewhere safe — it is your `GITHUB_APP_PRIVATE_KEY`

### 8.7 Install the app on your repository

1. On the GitHub App page, look for "Install App" in the left sidebar and click it
2. You will see your GitHub account listed — click "Install"
3. Select "Only select repositories"
4. Choose the repository `ai-code-reviewer` (and any other repos you want the bot to review)
5. Click "Install"

---

## 9. Phase 6 — LangFuse Setup

LangFuse is already wired into the orchestrator service code. No code changes needed — you just need your API keys.

### 9.1 Get your LangFuse API keys

1. Go to https://cloud.langfuse.com and log in
2. Click on your `ai-code-reviewer` project
3. Click "Settings" in the left sidebar
4. Click "API Keys"
5. Click "Create new API key"
6. Copy and save both:
   - **Public Key** — starts with `pk-lf-` — this is `LANGFUSE_PUBLIC_KEY`
   - **Secret Key** — starts with `sk-lf-` — this is `LANGFUSE_SECRET_KEY`

---

## 10. Phase 7 — OpenAI API Key

1. Go to https://platform.openai.com
2. Click your profile icon in the top right → "API keys"
3. Click "Create new secret key"
4. Name: `ai-code-reviewer`
5. Click "Create secret key"
6. Copy the key — it starts with `sk-proj-...` or `sk-...`
7. Save it. This is your `OPENAI_API_KEY`.

---

## 11. Phase 8 — Provision AWS Infrastructure with Terraform

This step creates all the AWS resources your system needs: the Kubernetes cluster, database, Redis, container registry, and storage. You only do this once.

### 11.1 Open CMD and navigate to the Terraform folder

```
cd "D:\MAJOR PROJECT KRISH SIR\ai-code-reviewer\infra\terraform"
```

### 11.2 Initialize Terraform

```
terraform init
```

This downloads all required providers and modules from the internet. You will see a lot of output. It finishes with:
```
Terraform has been successfully initialized!
```

If you see errors, check your internet connection and that you are in the correct folder.

### 11.3 Preview what Terraform will create

```
terraform plan -var="cluster_name=ai-code-reviewer" -var="db_password=YourStrongPassword123!" -var="environment=production"
```

Read through the output. It will show everything it plans to create:
- 1 VPC (virtual network on AWS)
- 1 EKS cluster with 2 worker nodes
- 1 RDS PostgreSQL database
- 1 ElastiCache Redis cluster
- 1 S3 bucket
- 5 ECR repositories (one per service)

If there are errors, check your AWS credentials:
```
aws sts get-caller-identity
```

### 11.4 Create everything on AWS

```
terraform apply -var="cluster_name=ai-code-reviewer" -var="db_password=YourStrongPassword123!" -var="environment=production"
```

Terraform will show the plan again and ask:
```
Do you want to perform these actions? Enter a value:
```

Type `yes` and press Enter.

**This takes 15 to 25 minutes.** The EKS cluster takes the longest to create. Leave CMD open and wait.

You will see lines like:
```
aws_vpc.main: Creating...
aws_eks_cluster.main: Creating...
aws_db_instance.postgres: Creating...
```

When it finishes you will see:
```
Apply complete! Resources: XX added, 0 changed, 0 destroyed.
```

### 11.5 Save all the output values

```
terraform output
```

Copy every line of the output and save it in a text file. It will look like:

```
eks_cluster_endpoint   = "https://XXXXX.gr7.us-east-1.eks.amazonaws.com"
rds_endpoint           = "ai-code-reviewer-postgres.XXXX.us-east-1.rds.amazonaws.com:5432"
redis_endpoint         = "ai-code-reviewer-redis.XXXX.cache.amazonaws.com:6379"
ecr_gateway_url        = "123456789012.dkr.ecr.us-east-1.amazonaws.com/gateway"
ecr_webhook_url        = "123456789012.dkr.ecr.us-east-1.amazonaws.com/webhook"
ecr_orchestrator_url   = "123456789012.dkr.ecr.us-east-1.amazonaws.com/orchestrator"
ecr_reviewer_url       = "123456789012.dkr.ecr.us-east-1.amazonaws.com/reviewer"
ecr_learner_url        = "123456789012.dkr.ecr.us-east-1.amazonaws.com/learner"
```

You will use these values in the next steps.

---

## 12. Phase 9 — Configure GitHub Secrets

These secrets are used by GitHub Actions when it automatically builds and deploys your code. You add them once and they are stored securely by GitHub.

### 12.1 Go to your repository secrets page

1. Go to https://github.com/YOUR_USERNAME/ai-code-reviewer
2. Click "Settings" (the tab at the top of the repo page)
3. In the left sidebar click "Secrets and variables"
4. Click "Actions"
5. Click "New repository secret"

### 12.2 Add every secret one by one

For each secret: click "New repository secret", enter the Name and Value, click "Add secret".

**AWS secrets — add these 3:**

| Name | Value |
|---|---|
| `AWS_ACCOUNT_ID` | your 12-digit number from Step 6.3 |
| `AWS_ROLE_ARN` | the full ARN from Step 6.5 — looks like `arn:aws:iam::123456789012:role/github-actions-ai-reviewer` |
| `EKS_CLUSTER_NAME` | `ai-code-reviewer` |

After adding all secrets, you should have **3 secrets** total: `AWS_ACCOUNT_ID`, `AWS_ROLE_ARN`, `EKS_CLUSTER_NAME`.

> **Note — `OPENAI_API_KEY` and `DATABASE_URL` do NOT go here:**
> The evaluate job runs inside the Kubernetes cluster and reads these values directly from `infra/k8s/secret.yaml` at runtime. They do not need to be GitHub Actions secrets.

> **Important — what does NOT go here:**
> - `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are NOT GitHub Actions secrets. No pipeline uses them. They go only into `infra/k8s/secret.yaml` in Phase 12 so Kubernetes pods can read them at runtime.
> - `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, `GITHUB_WEBHOOK_SECRET` also go only into `secret.yaml` — GitHub blocks secrets starting with `GITHUB_` in Actions.
> - The pipelines only build Docker images and run `kubectl set image`. They never create or update the Kubernetes secret. That is done once manually in Phase 12.

---

## 13. Phase 10 — First Deployment via GitHub Actions

> **IMPORTANT:** When you run the pipelines right now, only **test** and **build-and-push** jobs will succeed. The **deploy** job will fail with "deployment not found" — this is expected and normal. The deploy job requires Kubernetes deployments to already exist, which only happens after you complete Phase 12. Once you finish Phase 12, re-run the pipelines and all 3 jobs will pass.

### How the CI/CD pipelines work (per-service architecture)

This project uses **5 separate pipelines** — one per service. Each pipeline is independent:

| Pipeline file | Triggers when you change |
|---|---|
| `gateway.yml` | anything inside `services/gateway/` |
| `webhook.yml` | anything inside `services/webhook/` |
| `orchestrator.yml` | anything inside `services/orchestrator/` |
| `reviewer.yml` | anything inside `services/reviewer/` |
| `learner.yml` | anything inside `services/learner/` |

This means if you fix a bug in the orchestrator, only the orchestrator pipeline runs — the other 4 services are untouched. Each pipeline has the same 3 jobs: **test → build-and-push → deploy**.

### 13.1 Trigger all 5 pipelines for the first deployment

Because this is the first time, you need to trigger all 5 pipelines at once. The easiest way is to touch a file in each service:

Open CMD:

```
cd "D:\MAJOR PROJECT KRISH SIR\ai-code-reviewer"
```

```
git add services/
```

```
git commit -m "deploy: trigger initial deployment for all services"
```

```
git push origin main
```

This push touches all service directories so all 5 pipelines trigger simultaneously.

### 13.2 Watch the pipelines run

1. Go to https://github.com/data-guru0/MAJOR-PROJECT-KRISH-SIR
2. Click the "Actions" tab at the top
3. You will see **5 separate workflow runs** all starting at the same time — one per service
4. Click on any of them to watch it

Each workflow has three jobs in sequence:

**Job 1 — test (1-2 minutes)**
- Sets up Python 3.11
- Installs pip packages for that service only
- Runs pytest for that service only

**Job 2 — build-and-push (3-5 minutes)**
- Logs in to your AWS ECR
- Builds the Docker image for that service only
- Pushes it to ECR tagged with the git commit SHA

**Job 3 — deploy (1 minute)**
- Connects to your EKS cluster
- Runs `kubectl set image` for that service only

**All three jobs in all 5 workflows must show a green checkmark.**

If any job fails, click on it, then click on the failed step to read the error message.

### 13.3 Common first-deployment failures

**"Error: Could not assume role" or "Not authorized to perform sts:AssumeRoleWithWebIdentity"**

This means the OIDC trust relationship is not set up correctly.
Go back to Step 6.5 and check:
- The condition value exactly matches your GitHub username and repo name
- There are no typos — it must be `repo:data-guru0/MAJOR-PROJECT-KRISH-SIR:*`

**"Repository does not exist" for ECR**

Terraform did not finish creating the ECR repositories.
Go back to the terraform folder and run `terraform apply` again.

**"error: exec plugin: invalid apiVersion"**

Your kubectl version is incompatible. Download the latest version from https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/

### 13.4 Re-trigger all 5 pipelines after Phase 12 is complete

After you finish Phase 12 (applying all Kubernetes manifests), you must re-run all 5 pipelines so the deploy job can execute successfully. The deploy job requires the Kubernetes deployments to already exist.

Each service folder has a `deploy.txt` file specifically for this purpose. Increment the number inside it to trigger pipelines without touching any actual code:

```
cd "D:\MAJOR PROJECT KRISH SIR\ai-code-reviewer"
```

```
echo 2 > services\gateway\deploy.txt && echo 2 > services\webhook\deploy.txt && echo 2 > services\orchestrator\deploy.txt && echo 2 > services\reviewer\deploy.txt && echo 2 > services\learner\deploy.txt
```

```
git add services\
```

```
git commit -m "deploy: trigger all 5 pipelines after k8s setup"
```

```
git push origin main
```

Next time you need to trigger again, use `echo 3 >`, then `echo 4 >`, etc.

Go to GitHub → Actions tab and wait for all 3 jobs (test → build-and-push → deploy) in all 5 pipelines to show green checkmarks.

### 13.5 How to redeploy a single service later

When you change only one service, only that service's pipeline runs automatically. For example, if you edit `services/orchestrator/graph.py`:

```
git add services/orchestrator/graph.py
git commit -m "fix: improve security agent prompt"
git push origin main
```

Only the **Orchestrator CI/CD** pipeline runs. The other 4 services are not touched.

---

## 14. Phase 11 — Connect kubectl to EKS

kubectl is the command-line tool for managing your Kubernetes cluster. You need to configure it to talk to your EKS cluster on AWS.

### 14.1 Update your kubeconfig file

Open CMD and run:

```
aws eks update-kubeconfig --name ai-code-reviewer --region us-east-1
```

You will see:
```
Added new context arn:aws:eks:us-east-1:123456789012:cluster/ai-code-reviewer to C:\Users\YourName\.kube\config
```

This creates a config file on your machine that kubectl uses to connect to AWS.

### 14.2 Verify the connection

```
kubectl get nodes
```

You should see two nodes with STATUS = Ready:

```
NAME                          STATUS   ROLES    AGE   VERSION
ip-10-0-1-xxx.ec2.internal    Ready    <none>   5m    v1.29.x
ip-10-0-2-xxx.ec2.internal    Ready    <none>   5m    v1.29.x
```

If they show `NotReady`, wait 3 minutes and run the command again. EKS nodes take a few minutes to fully start.

If you see "no server found" or connection refused, your `aws configure` credentials may be wrong. Run `aws sts get-caller-identity` to check.

---

## 15. Phase 12 — Apply Kubernetes Manifests

This deploys all your services onto the EKS cluster.

### 15.1 Update the ConfigMap with your real Redis URL

**Why this matters:** The `configmap.yaml` file has a placeholder Redis URL. If you skip this step, all services will fail to connect to Redis (ElastiCache) and the entire system will return 500 errors silently.

First get your Redis endpoint from Terraform:
```
cd "D:\MAJOR PROJECT KRISH SIR\ai-code-reviewer\infra\terraform"
terraform output
```

Copy the `redis_endpoint` value. It looks like:
```
ai-code-reviewer-redis.khmhzg.0001.use1.cache.amazonaws.com:6379
```

Now open the ConfigMap file:
```
notepad "D:\MAJOR PROJECT KRISH SIR\ai-code-reviewer\infra\k8s\configmap.yaml"
```

Find this line:
```
REDIS_URL: "redis://redis:6379/0"
```

Replace it with your actual endpoint (remove the `:6379` from the endpoint since it's already in the URL):
```
REDIS_URL: "redis://YOUR_REDIS_ENDPOINT:6379/0"
```

Example:
```
REDIS_URL: "redis://ai-code-reviewer-redis.khmhzg.0001.use1.cache.amazonaws.com:6379/0"
```

Save the file.

### 15.2 Fill in the Kubernetes secret file

You need to open and edit `infra\k8s\secret.yaml` with your actual secret values.

Open CMD:

```
notepad "D:\MAJOR PROJECT KRISH SIR\ai-code-reviewer\infra\k8s\secret.yaml"
```

Replace all the empty values with your real values. The file should look like this when done:

```yaml
# Fill in all values before applying with: kubectl apply -f secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
stringData:
  GITHUB_WEBHOOK_SECRET: "myWebhookSecret_abc123XYZ789"
  GITHUB_APP_ID: "12345678"
  GITHUB_APP_PRIVATE_KEY: |
    -----BEGIN RSA PRIVATE KEY-----
    MIIEowIBAAKCAQEA1234...
    (all lines of your private key go here, keeping the line breaks)
    -----END RSA PRIVATE KEY-----
  OPENAI_API_KEY: "sk-proj-abc123..."
  LANGFUSE_PUBLIC_KEY: "pk-lf-abc123..."
  LANGFUSE_SECRET_KEY: "sk-lf-abc123..."
  DATABASE_URL: "postgresql+asyncpg://dbadmin:YourStrongPassword123!@ai-code-reviewer-postgres.abc123.us-east-1.rds.amazonaws.com/codereviewer"
```

**Important notes:**
- The `DATABASE_URL` here must use `postgresql+asyncpg://` (with asyncpg) — this is different from the one you put in GitHub secrets
- The private key must keep all its line breaks exactly as they are in the `.pem` file
- `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` go here only — do NOT add them to GitHub Actions secrets. The pipeline never touches this file. These keys are read directly by the orchestrator pod at runtime.
- Save the file: Ctrl+S, then close Notepad

### 15.2 Navigate to the k8s folder

```
cd "D:\MAJOR PROJECT KRISH SIR\ai-code-reviewer\infra\k8s"
```

### 15.3 Apply everything in exact order

Run each command. Wait for each one to complete before running the next.

**Step 1 — Apply the ConfigMap (non-secret environment variables):**
```
kubectl apply -f configmap.yaml
```
Expected output: `configmap/app-config created`

**Step 2 — Apply the Secrets:**
```
kubectl apply -f secret.yaml
```
Expected output: `secret/app-secrets created`

**Step 3 — Run the database migration:**

The `migration-job.yaml` always uses the `latest` tag which is automatically pushed by the webhook pipeline on every deployment. No manual changes needed.

Just apply it directly:
```
kubectl apply -f migration-job.yaml
```
Expected output: `job.batch/db-migrate created`

Now wait for the migration to finish — this creates all the tables in your RDS database:
```
kubectl wait --for=condition=complete job/db-migrate --timeout=120s
```
Expected output: `job.batch/db-migrate condition met`

If it times out, check what happened:
```
kubectl logs job/db-migrate
```

**Step 4 — Deploy all 5 services:**
```
kubectl apply -f gateway.yaml
kubectl apply -f webhook.yaml
kubectl apply -f orchestrator.yaml
kubectl apply -f reviewer.yaml
kubectl apply -f learner.yaml
```

**Step 5 — Deploy the Celery workers:**
```
kubectl apply -f webhook-worker.yaml
kubectl apply -f learner-worker.yaml
```

**Step 6 — Apply the autoscaler for orchestrator:**
```
kubectl apply -f hpa.yaml
```

**Step 7 — Install AWS Load Balancer Controller (required for ingress):**

This controller is what creates the AWS ALB from your ingress definition. Without it the ingress will have no ADDRESS forever.

```
helm repo add eks https://aws.github.io/eks-charts
helm repo update
```

```
helm install aws-load-balancer-controller eks/aws-load-balancer-controller -n kube-system --set clusterName=ai-code-reviewer --set serviceAccount.create=true
```

Wait 2 minutes for the controller to start:
```
kubectl get pods -n kube-system
```

All pods should show `Running`.

**Step 8 — Apply the ingress (creates your public URL):**
```
kubectl apply -f ingress.yaml
```

### 15.4 Verify all pods are running

```
kubectl get pods
```

Wait 3-5 minutes for all pods to start. Run this command multiple times until all show `Running`:

```
NAME                                READY   STATUS    RESTARTS   AGE
gateway-7d4f9b-xxx                  1/1     Running   0          3m
gateway-7d4f9b-yyy                  1/1     Running   0          3m
webhook-6c8d7b-xxx                  1/1     Running   0          3m
webhook-6c8d7b-yyy                  1/1     Running   0          3m
webhook-worker-5f6g7h-xxx           1/1     Running   0          2m
orchestrator-9h2j3k-xxx             1/1     Running   0          3m
orchestrator-9h2j3k-yyy             1/1     Running   0          3m
reviewer-4l5m6n-xxx                 1/1     Running   0          3m
reviewer-4l5m6n-yyy                 1/1     Running   0          3m
learner-7p8q9r-xxx                  1/1     Running   0          3m
learner-7p8q9r-yyy                  1/1     Running   0          3m
learner-worker-2s3t4u-xxx           1/1     Running   0          2m
```

If any pod shows `CrashLoopBackOff` or `Error`, see the Troubleshooting section at the end.

### 15.5 Get your public URL

```
kubectl get ingress gateway-ingress
```

Run this every minute for about 3 minutes. When the ADDRESS column shows a value, your system is live:

```
NAME              CLASS   HOSTS   ADDRESS                                                  PORTS
gateway-ingress   alb     *       k8s-default-gateway-abc123.us-east-1.elb.amazonaws.com   80,443
```

Copy the ADDRESS value and save it. This is your system's public URL.
Your full webhook endpoint is: `https://ADDRESS/webhook/github`

Note: If ADDRESS is empty, wait 3-5 minutes and run the command again. The ALB takes time to provision.

---

## 16. Phase 13 — Set Up Grafana and Prometheus

Grafana is the dashboard UI. Prometheus is what collects metrics from your services. You install both on your EKS cluster using Helm.

### 16.1 Add Helm chart repositories

Open CMD and run:

```
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
```

```
helm repo add grafana https://grafana.github.io/helm-charts
```

```
helm repo update
```

### 16.2 Install EBS CSI Driver (required for Prometheus storage)

Prometheus needs persistent storage. EKS requires the EBS CSI driver to provision EBS volumes for pods.

**Step 1 — Get your node group role name:**
```
aws eks list-nodegroups --cluster-name ai-code-reviewer --region us-east-1
```
```
aws eks describe-nodegroup --cluster-name ai-code-reviewer --nodegroup-name YOUR_NODEGROUP_NAME --region us-east-1
```
Look for the `nodeRole` field — copy just the role name after the last `/`. It looks like `default-eks-node-group-XXXXXXXXXXXX`.

**Step 2 — Attach the EBS CSI policy to the node group role:**

**Windows CMD:**
```
aws iam attach-role-policy ^
  --role-name YOUR_NODE_ROLE_NAME ^
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy
```

**Mac/Linux:**
```
aws iam attach-role-policy \
  --role-name YOUR_NODE_ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy
```

**Step 3 — Install the EBS CSI driver addon:**
```
aws eks create-addon --cluster-name ai-code-reviewer --addon-name aws-ebs-csi-driver --region us-east-1
```

**Step 4 — Wait until it shows ACTIVE:**
```
aws eks describe-addon --cluster-name ai-code-reviewer --addon-name aws-ebs-csi-driver --region us-east-1 --query addon.status --output text
```

Run Step 4 every minute until it shows `ACTIVE` before proceeding.

Wait until output shows `"ACTIVE"` before proceeding.

### 16.3 Install Prometheus

**Windows CMD:**
```
helm install prometheus prometheus-community/prometheus ^
  --namespace monitoring --create-namespace ^
  --set server.persistentVolume.size=8Gi ^
  --set server.persistentVolume.storageClass=gp2 ^
  --set alertmanager.persistence.storageClass=gp2
```

**Mac/Linux:**
```
helm install prometheus prometheus-community/prometheus \
  --namespace monitoring --create-namespace \
  --set server.persistentVolume.size=8Gi \
  --set server.persistentVolume.storageClass=gp2 \
  --set alertmanager.persistence.storageClass=gp2
```

This installs Prometheus in a new namespace called `monitoring`. Wait about 2 minutes.

Check that it is running:
```
kubectl get pods -n monitoring
```

All pods should show `Running`. It may take a few minutes.

### 16.4 Apply your Prometheus scrape config

Your project already has a config file that tells Prometheus where to find all 5 services. Apply it:

```
kubectl create configmap prometheus-config --from-file=prometheus.yml="D:\MAJOR PROJECT KRISH SIR\ai-code-reviewer\monitoring\prometheus.yml" -n monitoring --dry-run=client -o yaml | kubectl apply -f -
```

### 16.5 Install Grafana

Grafana needs NLB annotations so the AWS Load Balancer Controller assigns it a public IP. Without these annotations the EXTERNAL-IP stays `<pending>` forever.

If Grafana is already installed from a previous attempt, uninstall it first:
```
helm uninstall grafana -n monitoring
```

**Windows CMD:**
```
helm install grafana grafana/grafana ^
  --namespace monitoring ^
  --set persistence.enabled=true ^
  --set persistence.size=5Gi ^
  --set persistence.storageClassName=gp2 ^
  --set service.type=LoadBalancer ^
  --set "service.annotations.service\.beta\.kubernetes\.io/aws-load-balancer-type=external" ^
  --set "service.annotations.service\.beta\.kubernetes\.io/aws-load-balancer-nlb-target-type=ip" ^
  --set "service.annotations.service\.beta\.kubernetes\.io/aws-load-balancer-scheme=internet-facing"
```

**Mac/Linux:**
```
helm install grafana grafana/grafana \
  --namespace monitoring \
  --set persistence.enabled=true \
  --set persistence.size=5Gi \
  --set persistence.storageClassName=gp2 \
  --set service.type=LoadBalancer \
  --set "service.annotations.service\.beta\.kubernetes\.io/aws-load-balancer-type=external" \
  --set "service.annotations.service\.beta\.kubernetes\.io/aws-load-balancer-nlb-target-type=ip" \
  --set "service.annotations.service\.beta\.kubernetes\.io/aws-load-balancer-scheme=internet-facing"
```

Wait 2-3 minutes then check:
```
kubectl get svc grafana -n monitoring
```
The EXTERNAL-IP column shows a URL when the NLB is ready.

### 16.6 Get the Grafana admin password

Run this command — it will print the password in your CMD window:

```
kubectl get secret --namespace monitoring grafana -o jsonpath="{.data.admin-password}" > %TEMP%\grafana_pass.txt && certutil -decode %TEMP%\grafana_pass.txt %TEMP%\grafana_pass_decoded.txt && type %TEMP%\grafana_pass_decoded.txt
```

If that command is complex, use this simpler alternative — install Git Bash and run:
```
kubectl get secret --namespace monitoring grafana -o jsonpath="{.data.admin-password}" | base64 --decode
```

Save the password that gets printed. The username is always `admin`.

### 16.7 Get the Grafana URL

```
kubectl get svc -n monitoring grafana
```

Wait 2-3 minutes. The EXTERNAL-IP column will show a URL like `xxx.us-east-1.elb.amazonaws.com`.
Open your browser and go to: `http://EXTERNAL-IP`

### 16.8 Log in to Grafana

1. Open the Grafana URL in Chrome or any browser
2. You will see a login page
3. Username: `admin`
4. Password: the one you got in step 16.5
5. You will be asked to change your password — set a new one and save it

### 16.9 Add Prometheus as a data source

1. In Grafana, look at the left sidebar and click the gear icon (Configuration)
2. Click "Data sources"
3. Click "Add data source"
4. Click "Prometheus"
5. In the URL field enter: `http://prometheus-server.monitoring.svc.cluster.local`
6. Scroll down and click "Save & Test"
7. You should see a green message: "Data source is working"

### 16.10 Import your pre-built dashboard

Your project already has a complete Grafana dashboard saved as a JSON file.

1. In Grafana, click the "+" icon in the left sidebar
2. Click "Import"
3. Click "Upload JSON file"
4. Navigate to `D:\MAJOR PROJECT KRISH SIR\ai-code-reviewer\monitoring\grafana-dashboard.json`
5. Select the Prometheus data source you just added
6. Click "Import"

You now have a live dashboard showing 5 sections — one for each service. Each section has three panels:
- **Request Rate** — how many HTTP requests per minute each service is receiving
- **p99 Latency** — the response time for the slowest 1% of requests (tells you if something is slow)
- **Error Rate** — how many 5xx errors per minute (tells you if something is broken)

The dashboard updates automatically every 30 seconds.

---

## 17. Phase 14 — Set Up LangFuse Tracing

LangFuse is already wired into the orchestrator code. You need to point it at the correct host and make sure the keys in the Kubernetes secret are valid.

### 17.1 Check your LangFuse region

LangFuse has two regions. Log in at https://langfuse.com and check the URL your browser shows after login:
- `cloud.langfuse.com` → you are on the **EU** region
- `us.cloud.langfuse.com` → you are on the **US** region

### 17.2 Update configmap.yaml with the correct host

Open `infra/k8s/configmap.yaml` and set `LANGFUSE_HOST` to match your region:

**EU:**
```yaml
LANGFUSE_HOST: "https://cloud.langfuse.com"
```

**US:**
```yaml
LANGFUSE_HOST: "https://us.cloud.langfuse.com"
```

Save the file, then apply it and restart the orchestrator:
```
kubectl apply -f infra/k8s/configmap.yaml
kubectl rollout restart deployment orchestrator
```

### 17.3 Verify the Langfuse keys in the Kubernetes secret

The keys are stored in the Kubernetes secret `app-secrets` (set during Phase 12). They are NOT read from GitHub Actions secrets — the pipeline never touches `app-secrets`.

If you generated new LangFuse keys after Phase 12, you must update the secret manually:
```
kubectl get secret app-secrets -o jsonpath='{.data.LANGFUSE_PUBLIC_KEY}' | base64 --decode
```

If the key shown is wrong, update it:
```
kubectl create secret generic app-secrets --dry-run=client -o yaml ^
  --from-literal=LANGFUSE_PUBLIC_KEY=pk-lf-YOUR-KEY ^
  --from-literal=LANGFUSE_SECRET_KEY=sk-lf-YOUR-KEY ^
  | kubectl apply -f -
kubectl rollout restart deployment orchestrator
```

### 17.4 Verify traces are appearing

After opening a PR, check orchestrator logs for errors:
```
kubectl logs -l app=orchestrator --tail=50 | grep -i "langfuse\|401\|export"
```

`Failed to export span batch code: 401` means either wrong keys or wrong host region. Fix using 17.2 and 17.3.

### 17.5 Open the LangFuse dashboard

Go to your region URL and log in → click your `ai-code-reviewer` project → **Traces** in the left sidebar.

After a PR is analyzed you will see:
- One trace per PR
- 4 spans inside each trace running in parallel (static_analysis, security, style, architecture)
- Exact prompt sent and response received per span
- Token count, cost, and latency per call

---

## 18. Phase 15 — Update GitHub App Webhook URL

Now that your system is deployed and you have a public URL, you need to tell GitHub where to send webhook events.

### 18.1 Update the webhook URL in your GitHub App

First get your ingress address:
```
kubectl get ingress gateway-ingress
```

Your current ingress address is:
```
k8s-default-gatewayi-d0c66c7699-299311758.us-east-1.elb.amazonaws.com
```

Your full webhook URL is:
```
http://k8s-default-gatewayi-d0c66c7699-299311758.us-east-1.elb.amazonaws.com/webhook/github
```

Now update the GitHub App:
1. Go to GitHub → click your profile picture → Settings
2. Left sidebar → "Developer settings" → "GitHub Apps"
3. Click "Edit" next to `ai-code-reviewer-bot`
4. Find the "Webhook URL" field
5. Delete `https://placeholder.com`
6. Enter: `http://k8s-default-gatewayi-d0c66c7699-299311758.us-east-1.elb.amazonaws.com/webhook/github`
7. The "Webhook secret" field should still have the value you set in Step 8.2 — do not change it
8. Click "Save changes"

Your system is now fully connected. GitHub will send events to your running service.

---

## 19. Phase 16 — End-to-End Test

### 19.1 Install the GitHub App on your test repository

The GitHub App must be installed on whichever repository you want the bot to review.

1. Go to GitHub → click your profile picture → **Settings**
2. Left sidebar → **Developer settings** → **GitHub Apps**
3. Click **Edit** next to `ai-code-reviewer-bot`
4. Left sidebar → click **Install App**
5. Click **Install** next to your account
6. Select **Only select repositories**
7. Choose the repository you want to test with (e.g. `gmail-ai-analyze`)
8. Click **Install**

### 19.2 Make sure all pods are Running

Before testing, confirm every service is up:

```
kubectl get pods
```

All pods must show `Running`. If any show `Pending` or `CrashLoopBackOff`, wait and run again.

### 19.3 Trigger all 5 pipelines and wait for green

Increment the deploy.txt files to trigger all pipelines:

```
cd "D:\MAJOR PROJECT KRISH SIR\ai-code-reviewer"
```

```
echo 2 > services\gateway\deploy.txt && echo 2 > services\webhook\deploy.txt && echo 2 > services\orchestrator\deploy.txt && echo 2 > services\reviewer\deploy.txt && echo 2 > services\learner\deploy.txt
```

```
git add services\
git commit -m "deploy: trigger all pipelines for end-to-end test"
git push origin main
```

Go to GitHub → **Actions** tab. Wait until all 5 pipelines show green checkmarks on all 3 jobs (test → build-and-push → deploy).

Then run again and confirm all pods are `Running`:
```
kubectl get pods
```

### 19.4 Create a branch and open a Pull Request on your test repository

Do everything directly on the GitHub website — no CMD needed.

**Step 1 — Go to your test repository on GitHub**
(e.g. `https://github.com/YOUR_USERNAME/gmail-ai-analyze`)

**Step 2 — Create a new branch:**
1. Click the branch dropdown at the top left (shows `main`)
2. Type `test-ai-review` in the box
3. Click **"Create branch: test-ai-review"**

**Step 3 — Create a test file:**
1. Make sure you are on the `test-ai-review` branch
2. Click **"Add file"** → **"Create new file"**
3. Name the file `test_code.py`
4. Paste this code into the editor:
```python
def calculate(a,b):
    password = "admin123"
    result = eval(a+b)
    return result
```
5. Click **"Commit changes"** → **"Commit directly to test-ai-review branch"** → **"Commit changes"**

**Step 4 — Open a Pull Request:**
1. GitHub will show a yellow banner **"Compare & pull request"** — click it
2. Click **"Create pull request"**

**Step 5 — Wait 30-60 seconds**

The bot `ai-code-reviewer-bot` will automatically post review comments on the PR.

**Step 6 — Check for comments:**
1. Click the **"Files changed"** tab on the PR
2. You should see inline comments from `ai-code-reviewer-bot` pointing out issues like hardcoded password and dangerous use of `eval()`

If comments appear — your system is working end-to-end.

---

## 20. Accessing All Dashboards and UIs

### Grafana — Metrics Dashboard

**How to get the URL:**
```
kubectl get svc -n monitoring grafana
```
Copy the EXTERNAL-IP and open `http://EXTERNAL-IP` in your browser.

**Login:**
- Username: `admin`
- Password: the one you set in Step 16.7

**What to look at:**
- Select your imported dashboard from the dashboards list
- Each service has three panels: request rate, p99 latency, error rate
- If error rate spikes, something is broken
- If p99 latency spikes, something is slow
- Dashboard refreshes every 30 seconds automatically

---

### Prometheus — Raw Metrics

**How to open it (runs locally via port-forward):**

Open CMD and run:
```
kubectl port-forward -n monitoring svc/prometheus-server 9090:80
```
Keep this CMD window open. Then open your browser and go to: `http://localhost:9090`

**Useful queries to try:**
- Type `up` and click Execute — shows which services are being scraped (value 1 = up, 0 = down)
- Type `http_requests_total` — shows total request counts per service
- Type `rate(http_requests_total[5m])` — shows requests per second averaged over 5 minutes

Press Ctrl+C in the CMD window when you want to stop the port-forward.

---

### LangFuse — AI Call Tracing

**How to open:**
- EU accounts: https://cloud.langfuse.com
- US accounts: https://us.cloud.langfuse.com

Log in and click on the `ai-code-reviewer` project.

**Key sections:**
- **Traces** — one entry per PR analyzed. Shows the full timeline of all 4 agent calls.
- **Generations** — every individual OpenAI API call with full prompt and response
- **Dashboard** — total token usage, cost over time, average latency
- **Users** — which repos triggered the most analyses

---

### GitHub Actions — CI/CD Pipeline

**How to open:**
Go to https://github.com/YOUR_USERNAME/ai-code-reviewer and click the "Actions" tab.

**What to look at:**
- Every row is one deployment triggered by a `git push`
- Green checkmark = deployed successfully
- Red X = something failed — click to see which step failed and read the error

---

### Live Service Logs in CMD

To see what is happening inside any service right now, open CMD and run:

```
kubectl logs -l app=gateway -f
```

Replace `gateway` with any service name: `webhook`, `orchestrator`, `reviewer`, `learner`, `webhook-worker`, `learner-worker`

The `-f` flag means "follow" — it streams new log lines as they arrive, like a live tail. Press Ctrl+C to stop.

---

### Kubernetes Pod Status

To see the status of all running containers:
```
kubectl get pods
```

To see CPU and memory usage of each pod:
```
kubectl top pods
```

To see detailed information about a specific pod (useful for debugging crashes):
```
kubectl describe pod POD_NAME
```
Replace POD_NAME with an actual pod name from `kubectl get pods`.

---

## 21. How the Weekly Evaluation Works

Every Monday at 9am UTC, GitHub Actions automatically runs `scripts/evaluate.py`. This evaluates the quality of the AI-generated code review comments.

### What it does step by step:

1. Connects to your RDS PostgreSQL database using the DATABASE_URL secret
2. Queries the last 50 findings (AI comments) that were generated across all reviewed PRs
3. Builds a dataset from those findings
4. Runs RAGAS evaluation — a framework for measuring AI answer quality
5. Checks two metrics:
   - **Faithfulness** — are the comments grounded in the actual code diff?
   - **Answer Relevancy** — are the comments relevant to the question "what issues exist in this code?"
6. Prints the scores
7. If faithfulness score is below 0.7 (70%), the job fails and you get a notification email from GitHub

### How to see the evaluation results:

1. Go to GitHub → Actions tab
2. Look for the "Evaluate" workflow in the left sidebar
3. Click on the latest run
4. Click on the "evaluate" job
5. Expand the "Run evaluation" step
6. You will see output like:
   ```
   Mean faithfulness: 0.84
   ```

### What to do if it fails:

A score below 0.7 means the AI is generating low-quality or hallucinated comments.
To investigate:
1. Go to LangFuse → Traces
2. Look at the most recent PR analyses
3. Read the AI responses in each span
4. If the responses are off-topic, the system prompts in `services/orchestrator/graph.py` need tuning
5. If the responses are malformed JSON, the parsing in graph.py needs a fix

---

## 22. How to Check If Everything is Running

After the full setup, use these commands to verify your system is healthy.

**Check all pods are running:**
```
kubectl get pods
```
Every pod should show `Running` and `1/1` under READY.

**Check all Kubernetes services exist:**
```
kubectl get svc
```

**Check health endpoint of the gateway:**

Open a second CMD window and run:
```
kubectl port-forward svc/gateway 8000:8000
```

In your first CMD window run:
```
curl http://localhost:8000/health
```
Expected response: `{"status":"ok"}`

If `curl` is not available in CMD, open PowerShell and run:
```
Invoke-WebRequest -Uri http://localhost:8000/health
```

**Check the database tables were created:**
```
kubectl exec -it deployment/webhook -- python -c "import asyncio, sqlalchemy, os; from sqlalchemy.ext.asyncio import create_async_engine; e = create_async_engine(os.environ['DATABASE_URL']); asyncio.run(e.connect()).__enter__(); print('DB OK')"
```

**Check Prometheus is scraping your services:**
1. Open `http://localhost:9090` (after port-forwarding Prometheus from Step 20)
2. Click "Status" in the top menu → "Targets"
3. All 5 service targets (gateway, webhook, orchestrator, reviewer, learner) should show a green "UP" badge

---

## 23. Troubleshooting

### Pod shows `Pending` and never starts

```
kubectl describe pod POD_NAME
```
Look at the "Events" section at the bottom. Common causes:
- `Insufficient cpu` or `Insufficient memory` — your EKS nodes are out of capacity. Go to Terraform and increase `desired_size` to 3, run `terraform apply`.
- `ImagePullBackOff` — the Docker image does not exist in ECR. Go to GitHub Actions and re-run the `build-and-push` job.

### Pod shows `CrashLoopBackOff`

```
kubectl logs POD_NAME --previous
```
This shows the logs from before it crashed. Common causes:
- Wrong `DATABASE_URL` format — must start with `postgresql+asyncpg://`
- Missing environment variable — check that your `secret.yaml` has all the required keys and was applied
- Python import error — read the full traceback in the logs

### GitHub webhook deliveries are failing

1. Go to GitHub → Settings → Developer settings → GitHub Apps → ai-code-reviewer-bot
2. Click "Advanced" in the left sidebar
3. Under "Recent Deliveries" you can see every webhook event GitHub tried to send
4. Click on a failed delivery to see the HTTP response your server returned
5. Common causes:
   - `404` — the webhook URL path is wrong. It must end with `/webhook/github`
   - `401` — the webhook secret in your k8s secret does not match the one set in the GitHub App
   - Connection refused — the ingress is not created yet. Check `kubectl get ingress`

### AI review comments are not appearing on PRs

Check orchestrator logs:
```
kubectl logs -l app=orchestrator -f
```

Check reviewer logs:
```
kubectl logs -l app=reviewer -f
```

Common causes:
- OpenAI API key is invalid — check platform.openai.com/usage to see if calls are being made
- OpenAI account has no credits — add credits at platform.openai.com/billing
- GitHub App does not have Pull requests: Read and Write permission — check Step 8.3
- Private key format is wrong in secrets — the key must preserve line breaks

### Terraform fails with "Error: VPC limit exceeded"

AWS allows only 5 VPCs per region by default.
Either delete an old VPC in the AWS Console (VPC service → Your VPCs → delete one you do not need),
or request a limit increase: go to AWS Support → create a case → Service limit increase → VPC.

### kubectl commands fail with "error: You must be logged in to the server"

Your kubeconfig token has expired. Run this again:
```
aws eks update-kubeconfig --name ai-code-reviewer --region us-east-1
```

---

## 24. Cost Estimate

**Fixed monthly AWS costs (running 24/7):**

| Resource | Specification | Monthly Cost |
|---|---|---|
| EKS Cluster control plane | managed | $72 |
| EKS Worker Nodes | 2x t3.medium | $60 |
| RDS PostgreSQL | db.t3.micro, 20 GB | $15 |
| ElastiCache Redis | cache.t3.micro | $12 |
| Application Load Balancer | for ingress + Grafana | $18 |
| ECR storage | 5 repos, ~500 MB each | $1 |
| S3 bucket | minimal storage | $1 |
| **Total AWS per month** | | **~$179** |

**Usage-based costs:**

| Resource | Cost |
|---|---|
| OpenAI GPT-4o-mini | ~$0.15 per 100 PRs reviewed |
| LangFuse | Free up to 50,000 events/month |

**To pause the system and stop all charges:**
```
cd "D:\MAJOR PROJECT KRISH SIR\ai-code-reviewer\infra\terraform"
terraform destroy -var="cluster_name=ai-code-reviewer" -var="db_password=YourStrongPassword123!"
```
Type `yes` when asked. This deletes everything on AWS. You can recreate it later with `terraform apply`.

**To just scale down (reduce cost, keep data):**

Scale EKS nodes to 1:
- Open `infra\terraform\main.tf`
- Change `desired_size = 2` to `desired_size = 1`
- Run `terraform apply` again

---

## Quick Reference Card

```
Open Grafana:
  Run: kubectl get svc -n monitoring grafana
  Open: http://EXTERNAL-IP in browser
  Login: admin / your-password

Open Prometheus:
  Run: kubectl port-forward -n monitoring svc/prometheus-server 9090:80
  Open: http://localhost:9090 in browser
  (keep CMD window open while using it)

Open LangFuse:
  EU: https://cloud.langfuse.com
  US: https://us.cloud.langfuse.com

Check all pods:
  kubectl get pods

Watch live logs:
  kubectl logs -l app=gateway -f
  kubectl logs -l app=orchestrator -f
  kubectl logs -l app=reviewer -f

Deploy new code:
  git add .
  git commit -m "your message"
  git push origin main

Scale a service:
  kubectl scale deployment orchestrator --replicas=4

Shut down everything (stop AWS charges):
  cd "D:\MAJOR PROJECT KRISH SIR\ai-code-reviewer\infra\terraform"
  terraform destroy -var="cluster_name=ai-code-reviewer" -var="db_password=YourStrongPassword123!" -var="environment=production"
```

---

## 25. Teardown — Complete Cleanup

Run this when you want to shut everything down and stop all AWS charges.

### 25.1 Destroy all AWS infrastructure

```
cd "D:\MAJOR PROJECT KRISH SIR\ai-code-reviewer\infra\terraform"
```

```
terraform destroy -var="cluster_name=ai-code-reviewer" -var="db_password=YourStrongPassword123!" -var="environment=production"
```

Terraform will show everything it plans to delete and ask:
```
Do you really want to destroy all resources? Enter a value:
```

Type `yes` and press Enter. This takes 10-15 minutes.

### 25.2 Check for orphaned resources

Terraform sometimes misses resources that were created outside of it (like load balancers created by Kubernetes). Check and delete these manually:

**Load Balancers:**
```
aws elbv2 describe-load-balancers --query "LoadBalancers[].LoadBalancerArn" --output text
```
If anything is listed, delete each one:
```
aws elbv2 delete-load-balancer --load-balancer-arn YOUR_ARN
```

**EBS Volumes** (created by Prometheus/Grafana PVCs):
```
aws ec2 describe-volumes --filters "Name=status,Values=available" --query "Volumes[].VolumeId" --output text
```
If anything is listed, delete each one:
```
aws ec2 delete-volume --volume-id YOUR_VOLUME_ID
```

**CloudWatch Log Groups:**
```
aws logs describe-log-groups --log-group-name-prefix "/aws/eks" --query "logGroups[].logGroupName" --output text
```
Delete each one:
```
aws logs delete-log-group --log-group-name YOUR_LOG_GROUP
```

### 25.3 Verify nothing is left

```
aws ec2 describe-instances --query "Reservations[].Instances[].InstanceId" --output text
aws elbv2 describe-load-balancers --query "LoadBalancers[].LoadBalancerArn" --output text
```

Both should return empty. You are now fully cleaned up with zero ongoing charges.

### 25.4 To redeploy later

Just follow the documentation from Phase 8 onwards — run `terraform apply`, apply the k8s manifests, trigger the pipelines. Everything will come back up exactly as before.
