# Databricks CI/CD Learning

A hands-on learning repository for Git integration, bundles, and automated deployment.

**Start here:** [Follow-along lab: from Git integration to a running job](docs/follow-along-lab.md).

Repository: `https://github.com/pschehl/dbx-cicd-learning.git`. The repository, bundle, and deployment paths use `dbx-cicd-learning`.

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

For the complete exercise, follow the [lab](docs/follow-along-lab.md). For deployment details, follow [stage 2](docs/databricks-bundles.md) to authenticate, validate, deploy, and run your first bundle.

Repository structure (project files; generated files and Git internals omitted):

```text
dbx-cicd-learning/
├── README.md                         Project overview and starting point
├── .gitignore                        Excludes local state, caches, and environment files
├── databricks.yml                    Bundle targets, variables, paths, and run identities
├── .github/                          GitHub automation configuration
│   └── workflows/                    GitHub Actions workflow definitions
│       ├── ci-cd.yml                 Tests and ordered dev → staging → prod promotion
│       └── deploy.yml                Reusable bundle validation, deployment, and execution
├── docs/                             Setup references and practical exercises
│   ├── follow-along-lab.md           Step-by-step exercise from local run to CI/CD
│   ├── databricks-git-integration.md GitHub connection and working-copy synchronization
│   ├── databricks-bundles.md         Bundle configuration, deployment, and cleanup
│   └── cicd-workflow.md              CI authentication, promotion, failure, and recovery
├── resources/                        Databricks resource definitions included by the bundle
│   └── sales_job.yml                 Serverless job, task, and runtime parameter wiring
├── src/                              Application code uploaded with the bundle
│   └── sales_job.py                  Synthetic sales transformation and quality checks
└── tests/                            Local and CI tests; excluded from bundle upload
    └── test_sales_job.py             Calculation, input validation, and command-line tests
```

Local directories such as `.databricks/` (bundle state), `.venv/` (an optional Python environment), and `__pycache__/` (Python caches) may appear as you work. They are ignored by Git. `.git/` stores the checkout's version history and configuration.

The job prints a JSON result to task logs and writes no tables. CI deployments record the triggering Git commit; interactive deployments use `local` by default. Start with this small exercise before adding catalogs, schemas, persistent data, and migrations.

Configure CI authentication and GitHub environments before merging changes to `main`: the workflow attempts automatic promotion on every push to `main`. Start with a personal dev deployment in the lab.
