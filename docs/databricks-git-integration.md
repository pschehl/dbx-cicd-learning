# Connect this GitHub repository to Databricks

Prepared: 2026-09-28. Documentation checked against official sources on that date. UI labels and preview capabilities can change; use the linked sources when repeating this procedure.

**Stage 1 complete:** the user confirmed Git integration is done. This guide remains the setup reference. Continue with [stage 2: bundles](databricks-bundles.md), then [stage 3: CI/CD](cicd-workflow.md). The individual verification exercises below have not been independently observed by the assistant.

## 1. What you are connecting

Your laptop already has a Git repository with this remote:

```text
https://github.com/pschehl/databricks-cicd-learning.git
```

Databricks will have a second working copy, called a **Git folder**. Older tutorials call this **Repos**, and the Databricks CLI still uses `repos` commands. GitHub is the shared remote between the two copies. Git folders support editing notebooks/files and normal version-control operations. [Databricks concepts](https://docs.databricks.com/aws/en/repos/git-folders-concepts)

```text
Laptop working copy  -- push -->  GitHub  -- pull -->  Databricks Git folder
Laptop working copy  <-- pull --  GitHub  <-- push --  Databricks Git folder
```

Saving a file changes only the working copy where you edited it. Committing records a version there. Pushing publishes commits to GitHub. Pulling brings remote changes into the other copy. These transfers are explicit; editing on your laptop does not immediately change Databricks.

| Term | Meaning in this project |
| --- | --- |
| Repository | Files and their Git history |
| Remote / `origin` | The GitHub URL above; `origin` is its local nickname |
| Clone | Create another working copy from a remote |
| Branch | A named line of development, such as `main` |
| Commit | A recorded change with a message and identifier |
| Push | Upload local commits to the remote |
| Pull | Fetch remote commits and integrate them locally |
| Pull request (PR) | GitHub review process for merging a branch |

This connection versions project files. Data tables, compute, access permissions, secrets, and job configuration are separate resources unless you explicitly represent their configuration as code. Establishing Git access does not run your code or set up automatic deployments.

## 2. Setup record

Keep this table current after verifying the integration. Never record passwords or tokens here.

| Item | Value / status |
| --- | --- |
| Git provider | GitHub |
| Repository | `https://github.com/pschehl/databricks-cicd-learning.git` |
| GitHub owner | `pschehl` |
| Local folder | `/Users/p.schehl/Documents/databricks/dbx_git_integration` |
| Local branch inspected | `main` |
| Cloud provider | AWS (confirmed by user) |
| Workspace URL | `https://dbc-97622683-114b.cloud.databricks.com` |
| Workspace ID from supplied URL | `7474658421174687` |
| Databricks user | To be confirmed |
| Workspace Git folder path | Created by user; exact path not recorded |
| Git credential method | Not recorded; recommended method below is the GitHub app |
| Integration status | Completed, as confirmed by user |
| GitHub remote default branch | Verify in GitHub; local branch is `main` |
| Clone / read access verified | Pending |
| Databricks push verified | Pending |
| Laptop-to-workspace pull verified | Pending |
| Last successful verification | Pending |

At initial preparation, only `README.md` was tracked and `databricks` was not on the shell PATH. The user subsequently completed Git integration. The assistant has not independently run the synchronization checks.

## 3. Before starting

Open [your AWS Databricks workspace](https://dbc-97622683-114b.cloud.databricks.com). Have a Databricks login and a GitHub account with access to this repository. Use your own workspace user folder for this exercise. Creating a Git folder requires `CAN MANAGE` on its parent. [Creation prerequisites](https://docs.databricks.com/aws/en/repos/git-operations-with-repos)

There are two separate authentication relationships:

| Relationship | Purpose |
| --- | --- |
| You → Databricks | Open the workspace or use its API/CLI |
| Databricks → GitHub | Clone, pull, and push repository files |

Logging into Databricks does not automatically give it your laptop's GitHub credentials. Likewise, a Databricks access token is not a GitHub token.

## 4. Connect GitHub in the browser

1. In Databricks, open your user menu → **Settings** → **Linked accounts**.
2. Choose **Add Git credential**, provider **GitHub**, then **Link Git account**.
3. Complete GitHub authorization with the intended account.
4. Install/configure the **Databricks GitHub app** for owner `pschehl`. Choose **Only select repositories** and select `databricks-cicd-learning`.
5. Return to Databricks and confirm the Git credential appears.

User authorization and app installation are separate steps; both matter. If the repository belongs to an organization, its owner may need to approve access. Databricks recommends this app for hosted GitHub. This is the app installed in GitHub, independent of any assistant plugin. [GitHub connection instructions](https://docs.databricks.com/aws/en/repos/get-access-tokens-from-git-provider)

### Alternative: a GitHub personal access token

If account policy prevents app linking, create a fine-grained token in GitHub under **Settings → Developer settings → Personal access tokens**. Select the repository's resource owner, only this repository, an appropriate expiration, and **Contents: Read and write**. Add it as a Git credential in Databricks Linked accounts. Organization approval may apply. Enter the token directly in Databricks, never in this repository or chat. [Azure Databricks token setup](https://learn.microsoft.com/en-us/azure/databricks/repos/get-access-tokens-from-git-provider)

## 5. Create the workspace Git folder

In **Workspace**, navigate to your user folder, then select **Create → Git folder**. Enter:

| Field | Value |
| --- | --- |
| Repository URL | `https://github.com/pschehl/databricks-cicd-learning.git` |
| Provider | `GitHub` |
| Folder name | `databricks-cicd-learning` |
| Sparse checkout | Leave disabled for this small repository |

Create it, open the Git dialog, and check the branch is `main`. Record the actual workspace path. Confirm `README.md` appears. The documentation written locally will appear only after it has been committed, pushed, and pulled.

Each developer should use their own Git folder: switching a branch in a shared folder affects everyone using that folder. [Create and manage Git folders](https://learn.microsoft.com/en-us/azure/databricks/repos/git-operations-with-repos)

**Checkpoint:** seeing remote files verifies clone/read access. It does not yet prove push access or synchronization in both directions.

## 6. Practical exercise: prove both directions

Use a dedicated branch so the experiment is easy to review. The following commands are instructions to run, not a record of completed actions.

### A. Databricks → GitHub → laptop

1. In the Databricks Git dialog, create `learning/git-connection-check` from `main`.
2. Create a plain text file named `git-connection-check.txt` inside the Git folder with this content:

   ```text
   Created in Databricks to verify Git integration.
   ```

3. Review the Git diff. Commit and push with message `docs: verify Databricks Git connection`.
4. In GitHub, select that branch and confirm the file and commit exist.
5. On your laptop, run:

   ```bash
   cd /Users/p.schehl/Documents/databricks/dbx_git_integration
   git status
   git fetch origin
   git switch --track origin/learning/git-connection-check
   cat git-connection-check.txt
   ```

Before switching branches, preserve any local work. In particular, commit the newly prepared guide on its intended branch or temporarily stash it with untracked files included (`git stash push -u`); restore that stash on the original branch afterward. Do not discard documentation to run the exercise. If the exercise branch already exists locally, use `git switch learning/git-connection-check` instead.

### B. Laptop → GitHub → Databricks

Add this second line to `git-connection-check.txt` using your editor:

```text
Updated on my laptop to verify the return path.
```

Then run:

```bash
git diff -- git-connection-check.txt
git add git-connection-check.txt
git commit -m "docs: verify laptop changes reach Databricks"
git push
git rev-parse HEAD
```

In Databricks, stay on the same exercise branch, open the Git dialog, and **Pull**. Confirm both lines appear. Compare the latest commit identifier against GitHub and the laptop. Record success and date in section 2.

### C. Complete the exercise

Open a GitHub PR from `learning/git-connection-check` into `main`, review it, and merge when ready. Then switch both copies to `main` and pull. On the laptop, once your working tree is clean:

```bash
git switch main
git pull --ff-only origin main
```

You can later remove the exercise file with an ordinary reviewed commit. No compute execution is needed to inspect its contents.

## 7. Everyday workflow

For this project, use one feature branch per task and finish through a PR. Start from an updated `main` with a clean working tree:

```bash
git switch main
git pull --ff-only origin main
git switch -c feature/my-change
```

After editing and running checks appropriate to your change:

```bash
git status
git diff
git add path/to/changed-file
git commit -m "Describe the change"
git push -u origin feature/my-change
```

Replace the example filename before running `git add`. Open a PR in GitHub. Once merged, update each working copy explicitly. If you continue the same feature in Databricks, select that feature branch there and pull before editing.

The `--ff-only` option lets a pull advance your local branch only when no merge is needed. If it refuses, inspect the history instead of forcing the update. Avoid editing the same lines independently on both copies before synchronizing.

### Resolving a conflict

First preserve your uncommitted work. Fetch changes and inspect both versions. In a local merge conflict, edit each marked file to retain the intended combined result, remove conflict markers, test the result, stage the resolved files, and commit the merge. Push, then pull into the other copy. If a merge is in progress and you want to cancel that merge, `git merge --abort` is available; it is not a general undo command. For mistakes already shared, prefer a new corrective commit over rewriting history.

## 8. Optional repeatable setup with the Databricks CLI

Use this after understanding the browser workflow. The local Databricks CLI talks to the workspace API; Git credentials in the workspace still control GitHub access.

On macOS with Homebrew, install the current CLI:

```bash
brew tap databricks/tap
brew install databricks
databricks version
```

For an existing Homebrew installation, use `brew upgrade databricks`. Consult the official installer for other systems. [CLI installation](https://docs.databricks.com/aws/en/dev-tools/cli/install)

Authenticate interactively using the workspace base URL (remove notebook paths and browser query parameters):

```bash
databricks auth login --host https://dbc-97622683-114b.cloud.databricks.com
```

Choose profile name `dbx-git-learning` when prompted. Pass `--profile dbx-git-learning` to subsequent commands to target the intended workspace. This login is separate from the GitHub credential in section 4. [CLI authentication](https://docs.databricks.com/aws/en/dev-tools/cli/authentication)

The following uses the standard Repos API path convention `/Users/<email>/...`. Replace `<email>` with your actual workspace user identifier. Do not create a duplicate if the folder already exists.

```bash
databricks repos create \
  https://github.com/pschehl/databricks-cicd-learning.git gitHub \
  --path /Users/<email>/databricks-cicd-learning \
  --profile dbx-git-learning
```

Record the returned repo ID. For a standard Git folder, inspect it or update its checkout using:

```bash
databricks repos get <repo-id> --profile dbx-git-learning
databricks repos update <repo-id> --branch main --profile dbx-git-learning
```

`update` changes workspace contents; preserve pending edits first. This is an explicit update, not an automatic synchronization service. [Repos commands](https://docs.databricks.com/aws/en/dev-tools/cli/reference/repos-commands)

**Preview caveat:** current workspaces may create Git folders with Git CLI access when eligible. Those folders are not returned by List Repos, so an empty API listing does not prove the UI clone is absent. Use the UI to inspect it. Git CLI preview operations have compute requirements; follow current workspace-specific documentation rather than assuming every Git folder behaves identically. [Git CLI availability and limitations](https://docs.databricks.com/aws/en/repos/git-operations-with-repos)

## 9. Troubleshooting

| Symptom | Check / next action |
| --- | --- |
| Repository not found / access denied | Verify URL, GitHub identity, repository access, and whether the app installation includes this repository. |
| Clone works but push fails | Verify write access and branch protection; push a feature branch and use a PR if `main` is protected. |
| Works on laptop only | Check the workspace Git credential independently of your local Git login. |
| Workspace folder creation denied | Check permissions on the parent folder; start with your personal folder. |
| New local file absent in Databricks | Check it was committed and pushed; confirm the same branch and pull in Databricks. |
| Guide absent after first clone | The guide may still be local-only. Publish its commit, then pull the containing branch. |
| Push rejected after another update | Fetch and reconcile remote changes; do not force-push as a shortcut. |
| Pull reports conflicts | Preserve work and resolve the competing changes before retrying. |
| Git URL blocked or network timeout | Ask the workspace administrator to inspect Git allowlists and network access. |
| Correct repo but unexpected files | Compare branch and latest commit in all three places. |
| CLI targets another workspace | Check the selected profile and workspace host. |

Workspace administrators can control allowed Git URLs and network configuration. Provide the exact error and repository URL when asking for help, with secrets removed. [Workspace Git configuration](https://learn.microsoft.com/en-us/azure/databricks/repos/repos-setup)

Keep datasets and large generated artifacts outside Git; consult current limits before adding large assets or relying on advanced Git features. [Git folder limits](https://learn.microsoft.com/en-us/azure/databricks/repos/limits)

## 10. Repeat this in six months

- [ ] Confirm the intended repository URL and remote default branch.
- [ ] Confirm workspace URL, cloud, and user identity.
- [ ] Revisit current GitHub connection documentation.
- [ ] Check GitHub app installation still includes the repository.
- [ ] Reconnect an expired credential or rotate an expired PAT.
- [ ] Inspect an existing workspace Git folder before creating another.
- [ ] Confirm branch and pull the current code.
- [ ] Repeat the two-direction exercise on a fresh branch.
- [ ] Update the setup record with the actual path and verification date.
- [ ] Confirm the guide itself is committed and pushed so it survives loss of the laptop.

The GitHub app renews access tokens, but its refresh credential can expire after **six months of inactivity**. If returning after a long break, relink the account before assuming the repository or network is broken. [Credential lifecycle](https://docs.databricks.com/aws/en/repos/get-access-tokens-from-git-provider)

For a different repository, substitute its owner/name and repeat the app repository selection. For a different workspace or user, configure and verify credentials in that context rather than assuming the previous setup carries over.

## 11. What comes after this connection

Once the exercise succeeds, add notebooks or source files, tests, and a consistent PR process. Treat production deployment as a separate design decision: jobs and CI/CD should have an explicit deployment strategy and appropriate automation identities rather than depend on someone manually pulling a personal development folder. [CI/CD with Git folders](https://learn.microsoft.com/en-us/azure/databricks/repos/ci-cd-best-practices-with-repos)
