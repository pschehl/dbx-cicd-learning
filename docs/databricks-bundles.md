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

## How configuration, resources, and code fit together

Your understanding is broadly correct: `databricks.yml` is the entry point, it supplies the workspace and possible targets, and it loads the job definition from another YAML file. The important distinction is that configuration, workspace resources, and executable code have different roles.

| Setting or file | Responsibility in this repository |
| --- | --- |
| `bundle.name` | Names this bundle project: `dbx-cicd-learning`. |
| `workspace.host` | Identifies the Databricks workspace to deploy into. |
| `include` | Loads additional YAML configuration, here `resources/*.yml`. |
| `resources.jobs.sales_demo` | Defines the job that Databricks should create or update. |
| `targets` | Supplies deployment contexts: dev, staging, and prod. |
| `sync` | Controls synchronization of project files to the workspace. |
| Job `tasks` | Defines execution steps, their code references, and their settings. |
| `src/sales_job.py` | Implements the Python logic executed by our single task. |

The `resources/` directory is a project organization choice. The `resources:` YAML key is what declares workspace resources. The directory's name alone has no deployment behavior. A bundle can also describe other supported resources, such as pipelines, in addition to jobs. [Bundle configuration guide](https://docs.databricks.com/aws/en/dev-tools/bundles/settings)

### Does everything belong under `include`?

No. Top-level `include` lists additional **configuration files** to load:

```yaml
include:
  - resources/*.yml
```

Our job could instead be written directly under `resources:` in `databricks.yml`. Splitting it into `resources/sales_job.yml` makes the project easier to navigate. Both layouts describe the same job. Every additional YAML configuration file you want loaded must be covered by `include`; simply creating a YAML file somewhere in the repository is not sufficient.

Do not add `src/sales_job.py` to this top-level list. Python source is uploaded through file synchronization and referenced by a task. The configuration `include` is top-level only; environment-specific configuration belongs under `targets.<name>`, not under a target-specific configuration `include`.

The word “artifact” can mean any deliverable in conversation, but the bundle's actual `artifacts:` setting has a more specific purpose: describing build outputs such as Python wheels. This sample runs a plain Python script and does not need an `artifacts:` section. Targets can customize artifact settings if a future version of the project builds a package. [Configuration reference](https://docs.databricks.com/aws/en/dev-tools/bundles/reference)

### How do targets change what gets deployed?

The command selects **one target**, not every target listed in the file:

```bash
databricks bundle deploy -t dev -p dbx-git-learning
```

`dev` selects configuration from `targets.dev`; `dbx-git-learning` selects your saved login profile. A profile is an authentication alias, while a target is a deployment context. With no `-t`, this project selects dev because it has `default: true`.

Common configuration is combined with the selected target's settings. Our shared job definition uses variables, and each target supplies different batch sizes, thresholds, paths, and identities. A target can also specify its own workspace host when deploying to a different workspace. The current project deliberately uses one workspace for all three targets.

You can override resource settings directly under a target. For example, to give prod a longer job timeout, add `resources` inside the **existing** `targets.prod` mapping:

```yaml
# Illustrative fragment: merge into the existing targets mapping.
targets:
  prod:
    resources:
      jobs:
        sales_demo:
          timeout_seconds: 1800
```

The shared definition currently has a 900-second timeout. This override would make it 1800 for prod while dev and staging keep 900. `sales_demo` must match the resource key in `resources/sales_job.yml`; it is not the job's display name or numeric workspace ID. Do not add a second `targets:` or `prod:` key alongside the existing one.

You can also define a complete resource only inside `targets.dev.resources`, for example a dev-only diagnostic job. It then belongs only to that target. A shared resource remains present in all targets that inherit it; omitting it from a target override does not remove it.

Task overrides use the same job key and matching `task_key`. These settings are joined with the shared task; conflicting target settings take precedence. Do not assume every YAML list is simply replaced wholesale. Prefer the existing variables for values that vary by environment, and resource overrides for differences such as timeouts or task configuration. [Target and task override examples](https://docs.databricks.com/aws/en/dev-tools/bundles/overrides)

### Are the job's tasks inside `sales_job.py`?

The **task definition is in YAML**. The Python file contains the **implementation that task executes**. This job currently has one task:

```yaml
tasks:
  - task_key: transform_and_verify
    environment_key: default
    spark_python_task:
      python_file: ../src/sales_job.py
      # The full file also supplies command-line parameters here.
```

`task_key` identifies the step within the job. `spark_python_task` selects the Python script task type; our script itself uses ordinary Python and does not perform Spark processing. The source path is relative to `resources/sales_job.yml`, so `../src/sales_job.py` reaches the script in the sibling `src` directory. During this CLI deployment, the file is uploaded and the deployed task points to its workspace copy.

`environment_key: default` connects the task to the job's `environments` entry with the same key, which specifies serverless environment version 4. This execution environment is distinct from the bundle's dev/staging/prod deployment targets.

When the task runs, Python enters the script's `main()`, parses its arguments, calls `run_demo()`, and prints the result. `run_demo()` calls `summarize_orders()`. Those functions are internal code structure, not separate Databricks tasks. A raised quality-check error makes this single task fail.

A larger job can have multiple entries under `tasks`, each invoking a script, notebook, or another supported task type. Dependencies such as `depends_on: [{task_key: extract}]` specify execution order; list position alone does not establish an ordering. For example, you could eventually define extract → transform → verify as three independently observable tasks. [Job task types](https://docs.databricks.com/aws/en/dev-tools/bundles/job-task-types)

### Follow one parameter from YAML into Python

For the baseline dev deployment, the value travels through these layers:

```text
databricks.yml: targets.dev.variables.batch_size = "10"
    ↓ deployment-time substitution of ${var.batch_size}
sales_job.yml: job parameter batch_size defaults to "10"
    ↓ run-time reference {{job.parameters.batch_size}}
task arguments: --batch-size 10
    ↓ Python argparse converts the argument to an integer
sales_job.py: run_demo(..., batch_size=10, ...)
```

`${...}` is bundle configuration substitution. `{{job.parameters...}}` is a Databricks job run reference. The former sets the deployed default; the latter supplies the value for a particular execution, including any run override. [Bundle variables and job parameters](https://docs.databricks.com/aws/en/dev-tools/bundles/job-parameters)

### What is uploaded, and what actually runs?

This repository's synchronization configuration is:

```yaml
sync:
  include:
    - src/**
  exclude:
    - docs/**
    - tests/**
    - .github/**
```

`sync.include` controls source-file synchronization, independently of the top-level YAML configuration `include`. It supplements the default file selection based on the bundle root and `.gitignore`; it is **not an exclusive allowlist** saying only `src/` can be uploaded. The explicit exclusions keep the guides, tests, and Actions workflows out of source synchronization. Uploading a file does not execute it or turn it into a job resource. [File synchronization settings](https://docs.databricks.com/aws/en/dev-tools/bundles/settings#sync)

For this project, the lifecycle is:

| Action | Result |
| --- | --- |
| `python3 -m unittest discover -s tests -v` | Runs tests on your laptop, or on the Actions runner when CI invokes it. |
| `bundle validate -t dev` | Resolves and checks the selected configuration; creates no job and runs no sales code. |
| `bundle deploy -t dev` | Uploads files and creates or updates the dev job; does not execute this job. |
| `bundle run -t dev sales_demo` | Starts the deployed job and waits for its result; it does not redeploy local edits. |

Add `-p dbx-git-learning` to the bundle commands when using your personal CLI login. Run commands from the bundle root. To inspect the resolved configuration, use `databricks bundle validate -t dev -p dbx-git-learning -o json`.

Deployment state associates this bundle deployment with its workspace resources, so another deployment normally updates the existing job. Keep the bundle name and deployment root stable. After changing the script or deployed defaults, deploy again before running. A bundle target does not itself automate promotion: our GitHub Actions workflow explicitly deploys and runs dev, then staging, then prod. A Git folder pull only updates that editing copy and is not part of this CLI deployment sequence.

## Environment design

All three targets use the existing AWS workspace. They get distinct job names and deployment state paths.

| Target | Bundle mode | Orders | Minimum total (cents) | Identity |
| --- | --- | ---: | ---: | --- |
| `dev` | development | 10 | 2000 | Current deployer: you locally, service principal in CI |
| `staging` | production | 100 | 20000 | Configured service principal |
| `prod` | production | 1000 | 200000 | Configured service principal |

`staging` uses production mode so it exercises deployment behavior similar to prod. Target names are project choices; deployment modes control bundle behavior. Development mode adds a user-specific name prefix. [Deployment modes](https://docs.databricks.com/aws/en/dev-tools/bundles/deployment-modes)

Dev deployment state is under `/Workspace/Users/<deployer>/.bundle/dbx-cicd-learning/dev`. Shared state is under `/Workspace/Shared/.bundle/dbx-cicd-learning/staging` and `/Workspace/Shared/.bundle/dbx-cicd-learning/prod`.

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

The profile name `dbx-git-learning` is a local authentication alias used throughout these guides; it does not need to match the project name.

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

With the baseline configuration, dev produces 8 paid orders and 2000 cents; staging produces 80 and 20000; prod produces 800 and 200000. A threshold one cent above the expected total fails the run. The tests also exercise empty input and a batch size not divisible by five.

This is an end-to-end deployment exercise with a small in-memory transformation. Add Spark processing and environment-specific Unity Catalog schemas as a later extension when you want to test durable data isolation and data migrations.

The [follow-along lab](follow-along-lab.md#5-make-a-permanent-change-through-git) later changes dev to 20 orders and a 4000-cent threshold. After that edit, dev produces 16 paid orders and 4000 cents; staging and prod are unchanged.

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
