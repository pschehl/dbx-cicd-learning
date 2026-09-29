# Stage 3: end-to-end CI/CD

Updated 2026-09-29. Complete a personal dev run using the [bundle guide](databricks-bundles.md) first. This workflow is prepared in source; no GitHub Actions deployment has yet been verified.

The active configuration uses your personal account for learning in `pschehl/dbx-cicd-learning`. A production migration is described below.

## What happens for a change

1. A PR targeting `main` runs Python unit and command-line tests without Databricks credentials.
2. A push to `main` runs those tests again.
3. The reusable workflow validates, deploys, and runs `dev`.
4. Only a successful dev run allows the same sequence for `staging`.
5. Only successful staging allows `prod`; configured GitHub environment protection applies before its job starts.

All deployment stages check out the same triggering commit, `${{ github.sha }}`. This is source promotion: the Python file has no build step or external dependencies. The entire chain is serialized to keep concurrent revisions from interleaving. A manual dispatch on `main` runs the same chain; dispatch on another branch runs tests only.

`ci-cd.yml` defines the ordering. `deploy.yml` supplies the shared implementation. `bundle run` waits for completion; removing that wait would allow promotion before the job result was known. [Databricks GitHub Actions guidance](https://docs.databricks.com/aws/en/dev-tools/ci-cd/github)

## 1. Personal account setup for this learning exercise

You do not need Databricks admin rights if your user can create/use personal access tokens, create jobs, write to your own workspace folder, and run serverless jobs. Tokens cannot grant permissions your account does not already have. If token creation is disabled, an administrator must enable it or arrange another supported automation identity.

In your Databricks workspace, open **Settings → Developer → Access tokens → Manage → Generate new token**. Name it `github-dbx-cicd-learning` and choose a short lifetime suitable for the exercise. If the UI offers API scopes, choose scopes that support bundle deployment and execution (workspace files, jobs, and identity lookup), not a SQL-only token; follow the linked scope documentation for your workspace. Copy it directly into GitHub as described below. This is a **Databricks token**, not the GitHub PAT used for Git pushes. Never commit it or paste it in chat. [Token creation and workspace restrictions](https://docs.databricks.com/aws/en/dev-tools/auth/pat)

Your laptop can continue using browser-based OAuth with `dbx-git-learning`. GitHub's runner uses the token independently and has no access to your laptop profile. The workflow sets `DATABRICKS_AUTH_TYPE=pat` and reads `DATABRICKS_TOKEN` from an environment secret. No client ID, client secret, federation policy, or `id-token: write` permission is needed for this learning setup.

## 2. Configure GitHub environments

Open **repository Settings → Environments**. Create `dev`, `staging`, and `prod`. For **each** environment, add:

| Kind | Name | Value |
| --- | --- | --- |
| Environment variable | `DATABRICKS_HOST` | `https://dbc-97622683-114b.cloud.databricks.com` |
| Environment secret | `DATABRICKS_TOKEN` | Your Databricks personal access token |

For this exercise, the same workspace and personal token can be used in all three environments. The YAML reads `${{ vars.DATABRICKS_HOST }}` and `${{ secrets.DATABRICKS_TOKEN }}`; putting the token in Variables will not work. The reusable workflow selects its environment itself, so its job obtains the corresponding environment secret without a caller-level `secrets: inherit` setting.

Restrict deployment branches to `main`. Optionally configure a required reviewer for `prod`, if available for your repository and plan. Without this protection, prod proceeds automatically. For a solo exercise, preventing self-review requires another eligible reviewer; otherwise you cannot approve your own run. [GitHub environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments)

You need permission to manage these GitHub settings, even though Databricks admin rights are not required. No additional Databricks Git credential is needed by Actions: checkout retrieves the repository and the CLI uploads the code.

## 3. Understand the learning deployments

All targets deploy under your personal workspace directory:

```text
/Workspace/Users/<your-user-name>/.bundle/dbx-cicd-learning/dev
/Workspace/Users/<your-user-name>/.bundle/dbx-cicd-learning/staging
/Workspace/Users/<your-user-name>/.bundle/dbx-cicd-learning/prod
```

Dev uses development mode. Staging and prod omit `mode`; they are target names for practicing promotion, not real production environments. Production mode has additional identity/path checks intended for production deployments. Staging and prod explicitly run as the authenticated user and give that user `CAN_MANAGE`. [Deployment modes](https://docs.databricks.com/aws/en/dev-tools/bundles/deployment-modes)

Because CI and your laptop use the same user, bundle name, and dev root, **CI updates your existing personal dev deployment**. Avoid deploying locally while CI is running. Staging and prod have distinct paths and jobs. If you previously deployed using the older shared paths, this change creates new deployments; it does not migrate or delete the old resources.

## What each workflow does, and when

A GitHub Actions **workflow** is a YAML-defined automation. It contains **jobs**, which contain **steps**. The term CI/CD pipeline describes the overall sequence. A Databricks **job** is a separate workspace resource; in this repository it contains the Python task `transform_and_verify`.

### `ci-cd.yml`: trigger, tests, and promotion order

| Trigger | Behavior |
| --- | --- |
| Open/update a PR targeting `main` | Run tests only; deployment jobs are skipped. |
| Push to `main`, including a merged PR or docs-only commit | Run tests, then dev, staging, and prod in order. |
| Actions → CI and environment promotion → Run workflow on `main` | Run the full chain without requiring a new commit. |
| Manual dispatch on another branch | Run tests only. |

The `test` job starts an Ubuntu runner, checks out the code, installs Python 3.11, and runs `python -m unittest discover -s tests -v`. Tests do not require Databricks credentials or remote compute. In a PR, checkout normally tests GitHub's proposed merge result.

`dev` has `needs: test` and a condition limiting deployment to main outside PR events. `staging` needs successful dev; `prod` needs successful staging. Each calls `deploy.yml` with a different `target`. A failure skips dependent jobs. A configured environment approval waits before the deployment job starts.

The workflow's concurrency group serializes release runs; `cancel-in-progress: false` means an active release is not interrupted by a newer push. GitHub can replace pending runs with a newer pending run, so this is not a guarantee every pushed revision deploys. Separate PRs have separate concurrency groups. This coordination does not cover CLI deployments from your laptop.

### `deploy.yml`: reusable deployment implementation

This workflow uses `workflow_call`, so it is invoked by the main workflow rather than independently triggered by a push. Its `deploy` job selects `environment: ${{ inputs.target }}`, loads that environment's host and token, and has a 30-minute timeout.

| Step | Exactly what happens |
| --- | --- |
| Checkout | Retrieves `${{ github.sha }}` so all release stages deploy the same triggering commit. |
| Check environment configuration | Checks that host and token are nonempty and target is dev/staging/prod. It does not verify token validity. |
| Install CLI | Installs Databricks CLI 1.18.0 on the runner. |
| Validate resolved bundle | Authenticates and resolves the selected target, variables, resources, and user paths. |
| Deploy this revision | Uploads source files and creates/updates resources for that target. `--auto-approve` handles CLI prompts, not GitHub environment approvals. |
| Run and wait for quality checks | Executes `sales_demo` and waits for the remote task. A failed job causes this step and promotion to fail. |
| Record release | On success, writes the target, commit SHA, and workspace into the Actions summary. |

`BUNDLE_VAR_release_sha` supplies the triggering Git SHA as a deployment-time variable. The job prints it at runtime. Batch sizes and quality thresholds come from `databricks.yml`. Tests run on GitHub; the sales job runs on Databricks serverless compute and incurs workspace usage. Pulling your workspace Git folder is not part of this process.

A successful deploy followed by a failed run leaves the new job configuration deployed. There is no automatic rollback. The workflow contains no schedule; each main push/manual main dispatch invokes the chain once.

## 4. Review and publish the example

Review `git status` and `git diff` before staging changes. Use a feature branch, commit the intended files, push it, and open a PR into `main`. The bundle, sample code, tests, and workflows are already included in this repository.

The PR should run tests only. Configure the environment variables and token secrets before merging, because a push to `main` starts deployment automatically. Once merged, open **Actions → CI and environment promotion**.

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

In CI, `BUNDLE_VAR_release_sha` comes from the triggering revision. The token identifies the deploying user. Batch sizes and thresholds stay versioned in `databricks.yml` so a PR makes their changes visible.

## 7. Recovery and rollback

For a failed test, fix the source and push the PR again. For an authentication or permissions failure, correct external configuration and rerun the failed workflow. A retry uses the triggering revision; check its SHA before approving a delayed production run.

For a bad published change, revert its commit through a new PR and let the reverted code pass the entire promotion chain. This produces a new traceable commit with the previous behavior. There is no automatic rollback in these workflows.

If you cancel Actions while Databricks is running, inspect the Databricks run separately; stopping the runner is not a reliable way to cancel a remote job. Do not start another manual deployment against the shared target while CI is using it.

## Troubleshooting

| Failure | What to inspect |
| --- | --- |
| Missing environment variables | Variables belong under each GitHub environment, not only a local shell. |
| Token authentication rejected | Token expiration/revocation, workspace host, token scopes, and environment secret placement. |
| Workspace write denied | Deployment principal permissions on the root directory and existing job. |
| Run identity rejected | The token must belong to the user resolved by the CLI and that user must have job execution access. |
| Serverless task rejected | Workspace availability, principal entitlement, and supported environment version. |
| Prod starts without approval | Required reviewers were not configured or are unavailable for the plan/repository. |
| Unexpected personal job changes | CI and local dev share deployment state when using the same personal account. |
| Job succeeds but wrong revision | Compare `release_sha` and task source; check for out-of-band manual deployments. |
| Deployment lock held | Inspect other active deployments before retrying; do not force past a live lock. |

## Verification and six-month reference

| Item | Status / value |
| --- | --- |
| Workspace layout | Single AWS workspace; three deployments |
| Personal token stored in GitHub environment secrets | Pending setup |
| GitHub environments and branch restrictions | Pending setup |
| Personal job/serverless permissions | Pending verification |
| Production required reviewer | Pending setup / check plan availability |
| Successful workflow run URL and SHA | Pending |
| Failed-staging / skipped-prod run URL | Pending |
| Recovery run URL | Pending |
| Last end-to-end verification date | Pending |

When returning later, check CLI version compatibility, token expiration, user permissions, GitHub protection rules, serverless availability, and deployment paths. Rerun tests and dev before changing shared targets. CI currently pins CLI 1.18.0; update deliberately and rerun the exercise. The CLI installer action follows `main`; pin it to a reviewed commit when hardening this starter for long-term production use.

Next extensions: separate environment principals, Unity Catalog schemas and table-level permissions, Spark integration tests, dependency packaging, and genuinely separate workspaces if isolation requirements justify them.

## Production: migrate to a service principal and OIDC

For production workloads, use a dedicated service principal with workload identity federation (OIDC), ideally with permissions scoped per environment. This removes the dependency on your personal account and avoids storing a personal token in GitHub. Databricks recommends service principal run identities for production. [Run identity guidance](https://docs.databricks.com/aws/en/dev-tools/bundles/run-as)

This is a coordinated configuration change, not just replacing the token:

1. Have an account administrator create/assign the service principal and grant workspace, deployment-folder, and compute permissions.
2. Create federation policies with issuer `https://token.actions.githubusercontent.com`, audience your Databricks account ID, subject claim `sub`, and these subjects:
   - `repo:pschehl/dbx-cicd-learning:environment:dev`
   - `repo:pschehl/dbx-cicd-learning:environment:staging`
   - `repo:pschehl/dbx-cicd-learning:environment:prod`
3. Add its application ID as `DATABRICKS_CLIENT_ID` in each GitHub environment. Change the reusable workflow to `DATABRICKS_AUTH_TYPE: github-oidc`, read that client ID, and remove `DATABRICKS_TOKEN`. Update the configuration check accordingly.
4. Grant `id-token: write` to each calling deployment job and the reusable workflow; retain `contents: read`.
5. Configure bundle `run_as.service_principal_name` and permissions for the principal, controlled team deployment directories, and production mode for staging/prod. Plan deployment-state migration before changing existing paths or identities.
6. Verify dev, staging, and production approvals, then remove/revoke the learning token when no longer needed.

[Official GitHub OIDC setup](https://docs.databricks.com/aws/en/dev-tools/auth/provider-github)
