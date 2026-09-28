# Stage 2: deploy a Databricks bundle

Prepared 2026-09-28. Start here after completing [Git integration](databricks-git-integration.md). The workspace deployment is still pending; the example has local tests.

## What the bundle adds

A Declarative Automation Bundle describes resources and their source files in version control. The CLI deploys that definition to a workspace. The product was formerly called Databricks Asset Bundles; both names refer to the same tool family. [Bundle overview](https://docs.databricks.com/aws/en/dev-tools/bundles)

In this repository:

```text
databricks.yml                 Targets, variables, workspace paths, identities
resources/sales_job.yml         Job definition and parameter wiring
src/sales_job.py                Code uploaded with the deployment
tests/test_sales_job.py         Local checks, not part of the remote job
```

The deployed job runs the uploaded Python file. Pulling a workspace Git folder is not a deployment step in this example. The CLI deploys the copy from which you run it; in CI that is the checked-out commit.

## Environment design

All three targets use the existing AWS workspace. They get distinct job names and deployment state paths.

| Target | Bundle mode | Orders | Minimum total (cents) | Identity |
| --- | --- | ---: | ---: | --- |
| `dev` | development | 10 | 2000 | Current deployer: you locally, service principal in CI |
| `staging` | production | 100 | 20000 | Configured service principal |
| `prod` | production | 1000 | 200000 | Configured service principal |

`staging` uses production mode so it exercises deployment behavior similar to prod. Target names are project choices; deployment modes control bundle behavior. Development mode adds a user-specific name prefix. [Deployment modes](https://docs.databricks.com/aws/en/dev-tools/bundles/deployment-modes)

Dev deployment state is under `/Workspace/Users/<deployer>/.bundle/databricks-cicd-learning/dev`. Shared state is under `/Workspace/Shared/.bundle/databricks-cicd-learning/staging` and `/Workspace/Shared/.bundle/databricks-cicd-learning/prod`.

Your personal dev deployment and the CI service principal's dev deployment are intentionally different copies. Staging and prod have stable paths. Keep the bundle name and root paths stable after deployment: changing them can create a separate deployment rather than update the existing one.

These targets provide deployment separation within one workspace. They do not provide separate network or account boundaries. No schemas or tables are created by this exercise.

## Install and authenticate

Use Python 3.10+ and Databricks CLI 1.18.0 or newer. CI pins 1.18.0; use the same version when investigating differences. On macOS:

```bash
brew tap databricks/tap
brew install databricks
databricks version
databricks auth login --host https://dbc-97622683-114b.cloud.databricks.com
```

Name the profile `dbx-git-learning` when prompted. The browser login authorizes your CLI to access Databricks. It is separate from the GitHub connection already completed. [Install the CLI](https://docs.databricks.com/aws/en/dev-tools/cli/install), [CLI authentication](https://docs.databricks.com/aws/en/dev-tools/cli/authentication)

During preparation, CLI 1.18.0 was downloaded only to `/tmp/dbx-cli-1.18.0/databricks` for validation. That temporary copy is not a permanent installation and may disappear after cleanup/reboot.

The job assumes serverless jobs compute and serverless environment version 4 are available to the executing identity. Confirm this in your workspace before running. A Python script task uses `environment_key` to select its job environment; this example has no third-party libraries. [Serverless job example](https://docs.databricks.com/aws/en/dev-tools/bundles/examples)

## First local and remote run

Run these commands from the repository root:

```bash
python3 -m unittest discover -s tests -v
python3 src/sales_job.py --environment dev --batch-size 10 --min-total-cents 2000
databricks bundle validate -t dev -p dbx-git-learning
databricks bundle deploy -t dev -p dbx-git-learning
databricks bundle run -t dev -p dbx-git-learning sales_demo
```

`validate` checks the resolved configuration and needs authentication. `deploy` creates or updates the job and uploads code. `run` executes it and waits for completion; a failed run returns an error to the caller. Running serverless compute incurs normal workspace usage.

Expected task output includes:

```json
{
  "environment": "dev",
  "input_orders": 10,
  "paid_orders": 8,
  "quality_check": "passed",
  "release_sha": "local",
  "total_cents": 2000
}
```

Find the job in **Jobs & Pipelines**, open its latest run, and inspect the `transform_and_verify` task output. Record the job URL and run URL in the verification record below. The job does not persist output beyond logs.

## Understand the variable flow

There are three distinct configuration layers:

| Layer | Example | When used |
| --- | --- | --- |
| GitHub environment variable | `DATABRICKS_CLIENT_ID` | Authenticate the CI runner |
| Bundle variable | `${var.batch_size}` | Supply a job parameter default during deployment |
| Job parameter | `{{job.parameters.batch_size}}` | Supply the actual value to a task run |

The task receives `--batch-size` on its Python command line. `BUNDLE_VAR_release_sha` sets a bundle variable from CI. It becomes the job's `release_sha` default and appears in logs for traceability.

Bundle variable precedence is command-line `--var`, then `BUNDLE_VAR_*`, local variable-overrides file, target value, and global default. Bundle variables are deployment-time settings. A different run-time value should be passed as a job parameter. [Variables reference](https://docs.databricks.com/aws/en/dev-tools/bundles/variables)

Try a one-run override:

```bash
databricks bundle run -t dev -p dbx-git-learning sales_demo \
  --params batch_size=20,min_total_cents=4000
```

Expected total: 4000 cents from 16 paid orders. The deployed defaults remain unchanged. For a permanent change, edit the target variables in `databricks.yml`, then validate and redeploy.

## How the sample works

Every synthetic order has a value of 250 cents; every fifth order is cancelled. The transformation sums paid orders and rejects duplicate IDs, invalid amounts, and unknown statuses. Runtime checks verify the deterministic fixture and minimum accepted total. Integer cents avoid floating-point money arithmetic.

Dev therefore produces 8 paid orders and 2000 cents; staging produces 80 and 20000; prod produces 800 and 200000. A threshold one cent above the expected total fails the run. The tests also exercise empty input and a batch size not divisible by five.

This is an end-to-end deployment exercise with a small in-memory transformation. Add Spark processing and environment-specific Unity Catalog schemas as a later extension when you want to test durable data isolation and data migrations.

## Staging and prod prerequisites

Use [stage 3](cicd-workflow.md) to configure a CI service principal, workspace access, federation, and GitHub environments. CI supplies `BUNDLE_VAR_deploy_sp` with that principal's application ID and uses it as the staging/prod run identity.

The deployer needs access to create/update the bundle resources and write the shared deployment directories. The run identity needs permission to execute serverless jobs. Using a different deployer and run identity additionally requires permission to use that service principal. This starter keeps them the same in CI.

For a future move to separate workspaces, set a literal `workspace.host` under each target and update its corresponding GitHub `DATABRICKS_HOST`. Recreate the required identity access there. Authentication host fields do not support `${var...}` interpolation in CLI 1.18.0.

## Cleanup and recovery

To remove your personal example deployment, review the resources and run:

```bash
databricks bundle destroy -t dev -p dbx-git-learning
```

Read the CLI confirmation carefully. Use the same identity and target that created it. Destroying your personal dev copy does not remove CI's dev copy. Do not manually delete bundle state as a cleanup shortcut.

If a deployment fails, correct the configuration and redeploy with the same bundle name, identity, and path. If a run fails after a successful deploy, the deployed job remains; failure does not automatically roll back the deployment.

## Verification record

| Check | Status |
| --- | --- |
| Git integration | Completed by user |
| Python unit and CLI tests | 10 passed locally on 2026-09-28 |
| All three configured parameter sets | Passed locally; totals 2000 / 20000 / 200000 cents |
| Bundle structure | Checked against CLI 1.18.0 schema; authenticated validation remains pending |
| Authenticated bundle validation | Pending CLI login |
| Personal dev deployment and run | Pending |
| Serverless availability | To confirm in workspace |
| Dev job URL / run URL | Record after execution |
| Staging / prod deployment | Pending stage 3 |

Next: [build and exercise the CI/CD workflow](cicd-workflow.md).
