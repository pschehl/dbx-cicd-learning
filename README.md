# Databricks CI/CD Learning

A hands-on learning repository for Git integration, bundles, and automated deployment.

Prepared repository name: **`databricks-cicd-learning`**.

**GitHub rename pending:** open [repository settings](https://github.com/pschehl/dbx_git_integration/settings), change **Repository name** to `databricks-cicd-learning`, and click **Rename**. The available Git credential lacks repository administration permission, so this step could not be completed automatically. After renaming, update this checkout:

```bash
git remote set-url origin https://github.com/pschehl/databricks-cicd-learning.git
```

The guides already use the new repository name. The local folder remains `dbx_git_integration`; its name does not need to match GitHub. Existing Databricks Git folders may retain their old folder name. GitHub redirects Git operations from the old repository URL; use the new URL for future clones. [GitHub rename reference](https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository)

The project has three stages:

| Stage | Reference | Status |
| --- | --- | --- |
| 1. Connect GitHub to Databricks | [Git integration](docs/databricks-git-integration.md) | Completed by the user |
| 2. Define and deploy a Declarative Automation Bundle | [Bundle walkthrough](docs/databricks-bundles.md) | Example prepared; workspace deployment pending |
| 3. Test and promote through dev → staging → prod | [End-to-end CI/CD](docs/cicd-workflow.md) | Workflow prepared; authentication and live verification pending |

Declarative Automation Bundles were previously called Databricks Asset Bundles. This example uses one Python sales job, three bundle targets, environment-specific parameters, and GitHub Actions.

The configuration uses separate deployments in the existing AWS workspace: `https://dbc-97622683-114b.cloud.databricks.com`. These are learning environments, not separate workspace security boundaries.

```text
Feature branch → PR tests → merge to main → tests
                                           ↓
                                   deploy + run dev
                                           ↓
                                 deploy + run staging
                                           ↓
                              prod approval (configure in GitHub)
                                           ↓
                                  deploy + run prod
```

Run locally with Python 3.10+ and no third-party dependencies:

```bash
python3 -m unittest discover -s tests -v
python3 src/sales_job.py --environment dev --batch-size 10 --min-total-cents 2000
```

Then follow [stage 2](docs/databricks-bundles.md) to authenticate, validate, deploy, and run your first bundle.

| File | Purpose |
| --- | --- |
| `databricks.yml` | Targets, variables, deployment paths, and run identities |
| `resources/sales_job.yml` | Serverless job and runtime parameters |
| `src/sales_job.py` | Synthetic sales transformation and runtime quality checks |
| `tests/test_sales_job.py` | Local tests of calculations, validation, and CLI behavior |
| `.github/workflows/ci-cd.yml` | Tests and ordered environment promotion |
| `.github/workflows/deploy.yml` | Reusable validate/deploy/run steps |

The job prints a JSON result to task logs and writes no tables. Each deployment records its source revision. Start with this small exercise before adding catalogs, schemas, persistent data, and migrations.
