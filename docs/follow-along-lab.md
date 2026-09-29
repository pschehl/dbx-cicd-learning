# Follow-along lab: from Git integration to a running job

Start here if you have connected GitHub to Databricks but have not deployed anything yet. Run terminal commands on your laptop, from this repository's root, unless a step says otherwise. This lab uses the existing sample; you do not need to initialize another bundle.

Git integration gives you a workspace copy of your files. The bundle creates a runnable Databricks job. GitHub Actions later automates testing and deployment. These are separate steps:

```text
Laptop → test → bundle deploy → Databricks job → bundle run → task output
Laptop → commit/push → GitHub → Actions → dev → staging → prod
GitHub → explicit pull → Databricks Git folder (another editing copy)
```

The job generates synthetic sales orders, ignores cancelled orders, sums paid amounts, and checks a minimum total. It prints JSON to logs; it does not create a table or require input data. All targets currently use the same AWS workspace. Remote runs use billable serverless compute.

## 1. Run the example on your laptop

```bash
cd /Users/p.schehl/Documents/databricks/dbx-cicd-learning
python3 -m unittest discover -s tests -v
python3 src/sales_job.py --environment dev --batch-size 10 --min-total-cents 2000
```

Use Python 3.10 or newer. No pip installation is needed. Expect 10 passing tests and this result (JSON field order may differ):

```json
{"environment":"dev","input_orders":10,"paid_orders":8,"quality_check":"passed","release_sha":"local","total_cents":2000}
```

Open `src/sales_job.py`: each order is worth 250 cents and every fifth order is cancelled. Ten orders therefore produce eight paid orders worth 2000 cents.

**Checkpoint:** you can run and test the business logic without Databricks.

## 2. Install the CLI and log in to Databricks

On macOS with Homebrew:

```bash
brew tap databricks/tap
brew install databricks
databricks version
databricks auth login --host https://dbc-97622683-114b.cloud.databricks.com
```

If already installed through Homebrew, use `brew upgrade databricks`. This repository requires CLI 1.18.0 or newer. During browser login, save the profile as `dbx-git-learning` and choose your own workspace identity.

This login is independent of your GitHub PAT. It lets your laptop create and run workspace resources. [Official CLI authentication instructions](https://docs.databricks.com/aws/en/dev-tools/cli/authentication)

Confirm that your workspace and user can use serverless jobs compute; the sample selects serverless environment version 4. If unavailable, resolve that with your workspace administrator before the remote run.

## 3. Create and run your personal dev job

From the directory containing `databricks.yml`, run these one at a time. Continue only when the preceding command succeeds:

```bash
databricks bundle validate -t dev -p dbx-git-learning
databricks bundle deploy -t dev -p dbx-git-learning
databricks bundle run -t dev -p dbx-git-learning sales_demo
```

| Command | What you should observe |
| --- | --- |
| `validate` | Configuration resolves for the intended workspace and your identity. |
| `deploy` | A dev job is created and the Python source is uploaded. |
| `run` | The job executes and the command waits for its result. |

In Databricks, open **Jobs & Pipelines**, find the job whose name includes `dbx-cicd-learning-dev-sales` (development mode adds a user prefix), and open its latest run. Open task `transform_and_verify` and inspect its output. Expect the same JSON values as the local run.

The job uses the files uploaded by the bundle command. You do not need to pull your Databricks Git folder to update this deployment. Editing a file also does not update a deployed job until you deploy again. [Official bundle job tutorial](https://docs.databricks.com/aws/en/dev-tools/bundles/jobs-tutorial)

**Checkpoint:** record the job URL and successful run URL. You have now completed your first local-to-Databricks deployment. It is reasonable to stop here for your first session.

## 4. Change one run, then deliberately fail one

Run twice as many orders without changing the deployed defaults:

```bash
databricks bundle run -t dev -p dbx-git-learning sales_demo \
  --params batch_size=20,min_total_cents=4000
```

Expect 20 input orders, 16 paid orders, and 4000 cents. Now require one cent more than the generated data can produce:

```bash
databricks bundle run -t dev -p dbx-git-learning sales_demo \
  --params batch_size=20,min_total_cents=4001
```

Expect a failed run with `Quality check failed: 4000 < 4001 cents` in the task error. That is the intended result. Run the original command again to recover:

```bash
databricks bundle run -t dev -p dbx-git-learning sales_demo
```

Expect the original 10 orders and 2000 cents: one-run overrides did not change the defaults. No rollback or redeployment is needed for this exercise.

## 5. Make a permanent change through Git

First inspect `git status` and preserve any existing edits. From an up-to-date `main` with a clean working tree:

```bash
git switch main
git pull --ff-only origin main
git switch -c learning/dev-batch-20
```

In `databricks.yml`, change only the variables under `targets.dev`:

```yaml
    variables:
      batch_size: "20"
      min_total_cents: "4000"
```

Leave staging and prod unchanged. Run tests, validate, deploy, and run dev again using the commands above. This time a run with no overrides should produce 20 orders and 4000 cents. The tests also cover the original 10-order scenario; those remain valid.

```bash
git diff -- databricks.yml
git add databricks.yml
git commit -m "Increase personal dev sales example to 20 orders"
git push -u origin learning/dev-batch-20
```

Open a PR into `main` on GitHub. Under **Checks**, inspect the Python tests. In your Databricks Git folder, select the feature branch and pull to see the updated YAML there too.

**Before merging:** this repository's workflow automatically attempts dev → staging → prod on every push to `main`. Complete step 6 first if you want that deployment to succeed. A feature-branch PR runs tests without deploying.

## 6. Enable automatic promotion

Follow [CI/CD setup, sections 1–3](cicd-workflow.md#1-personal-account-setup-for-this-learning-exercise) to configure:

1. A personal Databricks token, if your workspace permits it.
2. GitHub environments `dev`, `staging`, and `prod`, each with a `DATABRICKS_HOST` variable and `DATABRICKS_TOKEN` secret.
3. Optional production approval if supported by your GitHub plan.

You need your existing job/serverless permissions and access to manage GitHub environment settings. No service principal or federation setup is needed for this learning route. If personal tokens are disabled, ask your workspace administrator about an approved automation method.

Then merge the PR. In **Actions → CI and environment promotion**, follow tests → dev → staging → prod. Approve prod if configured. Inspect each remote task output:

| Target | Input orders after this lab's change | Paid orders | Total cents |
| --- | ---: | ---: | ---: |
| dev | 20 | 16 | 4000 |
| staging | 100 | 80 | 20000 |
| prod | 1000 | 800 | 200000 |

Each output should show the same `release_sha`, matching the triggering commit. CI uses your personal identity and updates the same dev deployment as your laptop. Avoid deploying manually while CI is running.

To demonstrate a failed promotion and recovery, follow [the staging failure exercise](cicd-workflow.md#5-prove-a-failure-stops-promotion). Raising staging's threshold to 20001 should fail staging and skip prod. Restore it to 20000 through a follow-up PR. With this lab's dev change, dev still produces 4000 cents.

## 7. Keep a record and clean up when finished

Fill these in only after observing the results:

| Evidence | Your result |
| --- | --- |
| Local tests passed | Pending |
| Personal dev job and successful run URLs | Pending |
| Deliberate failed dev run URL | Pending |
| Feature PR URL | Pending |
| Successful promotion URL and commit SHA | Pending |
| Failed staging / skipped prod workflow URL | Pending |
| Recovery workflow URL | Pending |

To remove only your personal dev deployment when done:

```bash
databricks bundle destroy -t dev -p dbx-git-learning
```

Review the CLI confirmation before accepting. This leaves the Git repository and staging/prod deployments in place, but removes the dev deployment also used by CI. Use the existing [bundle reference](databricks-bundles.md) for configuration details and [CI/CD reference](cicd-workflow.md) for authentication and promotion troubleshooting.
