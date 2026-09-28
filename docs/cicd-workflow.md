# Stage 3: end-to-end CI/CD

Prepared 2026-09-28. Complete a personal dev run using the [bundle guide](databricks-bundles.md) first. This workflow is prepared in source; no GitHub Actions deployment has yet been verified.

The federation subjects below use the current repository, `pschehl/dbx-cicd-learning`. They must match the actual GitHub owner and repository name exactly. A Git URL redirect does not update federation policies.

## What happens for a change

1. A PR targeting `main` runs Python unit and command-line tests without Databricks credentials.
2. A push to `main` runs those tests again.
3. The reusable workflow validates, deploys, and runs `dev`.
4. Only a successful dev run allows the same sequence for `staging`.
5. Only successful staging allows `prod`; configured GitHub environment protection applies before its job starts.

All deployment stages check out the same triggering commit, `${{ github.sha }}`. This is source promotion: the Python file has no build step or external dependencies. The entire chain is serialized to keep concurrent revisions from interleaving. A manual dispatch on `main` runs the same chain; dispatch on another branch runs tests only.

`ci-cd.yml` defines the ordering. `deploy.yml` supplies the shared implementation. `bundle run` waits for completion; removing that wait would allow promotion before the job result was known. [Databricks GitHub Actions guidance](https://docs.databricks.com/aws/en/dev-tools/ci-cd/github)

## 1. Configure an automation identity

For this learning exercise, create one Databricks service principal named `dbx-cicd-learning-ci` and assign it to the existing workspace. Grant access to run serverless jobs and create/manage these job resources. Arrange write access to `/Workspace/Shared/.bundle/dbx-cicd-learning` and the principal's dev deployment directory. Record its **application/client ID**, not just its numeric object ID.

The workflow uses that identity for deployment and execution. For a production system, consider separate principals and narrower permissions per environment. Here, all three deployments share one workspace and one CI identity; the separation is organizational rather than a strong security boundary.

## 2. Trust GitHub Actions using OIDC

An account admin can open the [Databricks account console](https://accounts.cloud.databricks.com), select **User management → Service principals → your principal → Credentials & secrets → Federation policies**, and create policies. This establishes which external identity may authenticate as the principal. [Federation policy setup](https://docs.databricks.com/aws/en/dev-tools/auth/oauth-federation-policy)

Create one policy for each environment:

| Field | Value |
| --- | --- |
| Provider | GitHub Actions |
| GitHub owner | `pschehl` |
| Repository | `dbx-cicd-learning` |
| Entity type | Environment |
| Issuer | `https://token.actions.githubusercontent.com` |
| Audience | Your Databricks account ID |
| Subject for dev | `repo:pschehl/dbx-cicd-learning:environment:dev` |
| Subject for staging | `repo:pschehl/dbx-cicd-learning:environment:staging` |
| Subject for prod | `repo:pschehl/dbx-cicd-learning:environment:prod` |

Use the account ID from the account console; the numeric workspace ID in your browser URL is different. The workflow sets `DATABRICKS_AUTH_TYPE=github-oidc` and requests `id-token: write`. The CLI exchanges GitHub's short-lived token for Databricks access. No Databricks PAT is required. [GitHub OIDC instructions](https://docs.databricks.com/aws/en/dev-tools/auth/provider-github)

## 3. Configure GitHub environments

Before merging the workflow, open the repository's **Settings → Environments** and create `dev`, `staging`, and `prod`. In each, add these environment variables:

| Variable | Value in this exercise |
| --- | --- |
| `DATABRICKS_HOST` | `https://dbc-97622683-114b.cloud.databricks.com` |
| `DATABRICKS_CLIENT_ID` | Application ID of `dbx-cicd-learning-ci` |

Restrict deployment branches to `main`. On `prod`, configure a required reviewer if available. The YAML alone does not create an approval requirement. Without that protection, prod proceeds automatically after staging.

Availability of environments and required reviewers depends on repository visibility and your GitHub plan. If approvals are unavailable, this exercise can demonstrate automatic promotion, but should not be described as approval-gated. Review the current [GitHub environment settings](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments).

Set a branch rule requiring the workflow's test check before merging to `main`. GitHub branch rules and environment protections are configuration outside this repository; review them along with changes to workflow files.

## 4. Review and publish the example

Review `git status` and `git diff` before staging changes. Use a feature branch, commit the intended files, push it, and open a PR into `main`. The bundle, sample code, tests, and workflows are already included in this repository.

The PR should run tests only. Configure the environments and federation before merging, because a push to `main` starts deployment automatically. Once merged, open **Actions → CI and environment promotion**.

Observe each stage and approve prod if protection is enabled. In each Databricks job's task output, verify:

| Target | Input orders | Paid orders | Total cents |
| --- | ---: | ---: | ---: |
| dev | 10 | 8 | 2000 |
| staging | 100 | 80 | 20000 |
| prod | 1000 | 800 | 200000 |

These are the baseline values in the repository. If you completed the follow-along lab’s permanent dev change, expect 20 input orders, 16 paid orders, and 4000 cents for dev. Staging and prod remain as shown.

All three logs must show the same `release_sha`, matching the GitHub workflow revision. The Actions job summary records target, revision, and workspace after a successful run. Save the run URLs in the verification record.

## 5. Prove a failure stops promotion

First prove a successful run through all targets. Then create a PR changing only the staging `min_total_cents` in `databricks.yml` from `"20000"` to `"20001"`.

Expected result after merging:

1. Unit tests pass because the transformation remains correct.
2. Dev deploys and passes.
3. Staging deploys, but its runtime quality check fails: 20000 is less than 20001.
4. Prod is skipped; its previously deployed revision remains in place.

Staging will still contain the newly deployed configuration: stopping promotion does not undo a deployment. Restore the threshold to `"20000"` in a follow-up PR and merge. Confirm all three stages pass again. This exercise tests environment configuration and remote execution as well as source code tests.

## 6. Change a runtime parameter

Bundle variables determine the job's deployed defaults. Job parameters can override those defaults for one execution. For example, from your authenticated personal dev deployment:

```bash
databricks bundle run -t dev -p dbx-git-learning sales_demo \
  --params batch_size=20,min_total_cents=4000
```

In CI, `BUNDLE_VAR_release_sha` and `BUNDLE_VAR_deploy_sp` come from the triggering revision and environment identity. Batch sizes and thresholds stay versioned in `databricks.yml` so a PR makes their changes visible.

## 7. Recovery and rollback

For a failed test, fix the source and push the PR again. For an authentication or permissions failure, correct external configuration and rerun the failed workflow. A retry uses the triggering revision; check its SHA before approving a delayed production run.

For a bad published change, revert its commit through a new PR and let the reverted code pass the entire promotion chain. This produces a new traceable commit with the previous behavior. There is no automatic rollback in these workflows.

If you cancel Actions while Databricks is running, inspect the Databricks run separately; stopping the runner is not a reliable way to cancel a remote job. Do not start another manual deployment against the shared target while CI is using it.

## Troubleshooting

| Failure | What to inspect |
| --- | --- |
| Missing environment variables | Variables belong under each GitHub environment, not only a local shell. |
| OIDC authentication rejected | Exact federation subject, audience, client ID, workspace assignment, and `id-token` permission. |
| Workspace write denied | Deployment principal permissions on the root directory and existing job. |
| Run identity rejected | `deploy_sp` must be the application ID and the deployer must be allowed to use the identity. |
| Serverless task rejected | Workspace availability, principal entitlement, and supported environment version. |
| Prod starts without approval | Required reviewers were not configured or are unavailable for the plan/repository. |
| Personal job not updated by CI | Dev paths include the deploying identity; inspect CI's job, not your personal copy. |
| Job succeeds but wrong revision | Compare `release_sha` and task source; check for out-of-band manual deployments. |
| Deployment lock held | Inspect other active deployments before retrying; do not force past a live lock. |

## Verification and six-month reference

| Item | Status / value |
| --- | --- |
| Workspace layout | Single AWS workspace; three deployments |
| CI identity and application ID | Pending setup |
| GitHub environments and branch restrictions | Pending setup |
| Federation policies | Pending setup |
| Production required reviewer | Pending setup / check plan availability |
| Successful workflow run URL and SHA | Pending |
| Failed-staging / skipped-prod run URL | Pending |
| Recovery run URL | Pending |
| Last end-to-end verification date | Pending |

When returning later, check CLI version compatibility, identity membership, federation subjects, GitHub protection rules, serverless availability, and deployment paths. Rerun tests and dev before changing shared targets. CI currently pins CLI 1.18.0; update deliberately and rerun the exercise. The CLI installer action follows `main`; pin it to a reviewed commit when hardening this starter for long-term production use.

Next extensions: separate environment principals, Unity Catalog schemas and table-level permissions, Spark integration tests, dependency packaging, and genuinely separate workspaces if isolation requirements justify them.
