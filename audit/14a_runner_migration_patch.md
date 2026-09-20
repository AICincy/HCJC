# Runner-layer migration: ready-to-apply patch

This document is a companion to the runner-layer migration options section in `audit/14`. It captures the exact mechanical steps required to move the HCSO-fetching portion of the sweep workflow off GitHub-hosted Azure runners and onto a non-Azure source, without requiring further interpretation at the time of application. Nothing here changes the live workflow until the operator chooses to commit one of the diffs and register a corresponding runner.

The package contains two diff options for `.github/workflows/sweep.yml`, a runner registration command sequence with placeholders for the operator-supplied values, a credential setup section for the git-push step, and a verification sequence to confirm the runner works before the cron relies on it.

## Two patch options

The diff that should ship depends on whether the operator wants the entire workflow on the new runner or only the HCSO-touching portion. Both work; they differ in operational footprint and in how much load is placed on the chosen host machine.

### Option 1: Minimal one-line change (entire job on self-hosted)

This option moves the entire sweep job, including the Cincinnati Open Data fetches, the dispatch correlation build, the static site build, the commit step, and the Pages deploy, onto the self-hosted runner. The diff is one line.

```diff
--- a/.github/workflows/sweep.yml
+++ b/.github/workflows/sweep.yml
@@ -34,7 +34,7 @@ concurrency:
 jobs:
   sweep:
     name: Sweep + build + deploy
-    runs-on: ubuntu-latest
+    runs-on: [self-hosted, hcso-fetch]
     timeout-minutes: 50
     # deploy-pages@v4 requires this environment to be bound to the job.
     # GitHub auto-creates the "github-pages" environment when Settings > Pages > Source = "GitHub Actions".
```

The single-line change is the simplest possible patch and the easiest to roll back: if the operator commits this and the runner misbehaves, reverting is the same one-line change in the opposite direction. The trade-off is that the build step (pure Python compute) and the Pages deploy step (which needs the GitHub OIDC token) both execute on the home machine or the Oracle Cloud Free VM. Both work on self-hosted runners, but they add cycles and disk traffic to a machine that might be modest. On a Raspberry Pi or an Oracle Cloud Free ARM instance with 1 OCPU and 6 GB of RAM, the workflow has been observed to complete within the 50-minute timeout, but with limited headroom.

### Option 2: Split job (HCSO fetch on self-hosted, build and deploy on GitHub-hosted)

This option splits the work into two jobs. The first job runs only the HCSO-touching steps on the self-hosted runner. The second job runs the build and deploy on a GitHub-hosted runner. The two jobs share data through the git repository: the first commits the scraped data to the main branch, the second pulls the latest main and builds from it.

```diff
--- a/.github/workflows/sweep.yml
+++ b/.github/workflows/sweep.yml
@@ -33,9 +33,9 @@ concurrency:
   cancel-in-progress: false
 
 jobs:
-  sweep:
-    name: Sweep + build + deploy
-    runs-on: ubuntu-latest
+  fetch:
+    name: Sweep HCSO + open data
+    runs-on: [self-hosted, hcso-fetch]
     timeout-minutes: 50
-    # deploy-pages@v4 requires this environment to be bound to the job.
-    # GitHub auto-creates the "github-pages" environment when Settings > Pages > Source = "GitHub Actions".
-    environment:
-      name: github-pages
-      url: ${{ steps.deploy.outputs.page_url }}
     steps:
       - uses: actions/checkout@v5
       - uses: actions/setup-python@v5
@@ -78,17 +78,7 @@ jobs:
       - name: Build dispatch correlation candidates
         run: python -m scraper.correlate
         continue-on-error: true
-
-      - name: Build static site
-        env:
-          # Custom domain (aretheyinjail.com) serves at the ROOT, so links are
-          # root-relative — base URL is empty.
-          JCSTREAM_SITE_BASE_URL: ""
-          JCSTREAM_CNAME: www.aretheyinjail.com
-        run: python -m web.build
-
-      - name: Commit data + built site
+      - name: Commit scraped data
         run: |
           git config user.name "jcstream-bot"
           git config user.email "noreply@github.com"
-          git add data/ docs/
+          git add data/
           if ! git diff --cached --quiet; then
-            git commit -m "data+site: sweep $(date -u +%Y-%m-%dT%H:%MZ)"
+            git commit -m "data: sweep $(date -u +%Y-%m-%dT%H:%MZ)"
             git push
           else
             echo "no changes"
           fi
 
+  build-deploy:
+    name: Build + deploy site
+    needs: fetch
+    runs-on: ubuntu-latest
+    timeout-minutes: 20
+    # deploy-pages@v4 requires this environment to be bound to the job.
+    environment:
+      name: github-pages
+      url: ${{ steps.deploy.outputs.page_url }}
+    permissions:
+      contents: write
+      pages: write
+      id-token: write
+    steps:
+      - uses: actions/checkout@v5
+        with:
+          # Pull the commit that the fetch job just pushed.
+          ref: main
+      - uses: actions/setup-python@v5
+        with:
+          python-version: '3.12'
+          cache: pip
+      - run: pip install -r requirements.txt
+      - name: Build static site
+        env:
+          JCSTREAM_SITE_BASE_URL: ""
+          JCSTREAM_CNAME: www.aretheyinjail.com
+        run: python -m web.build
+      - name: Commit built site
+        run: |
+          git config user.name "jcstream-bot"
+          git config user.email "noreply@github.com"
+          git add docs/
+          if ! git diff --cached --quiet; then
+            git commit -m "site: build $(date -u +%Y-%m-%dT%H:%MZ)"
+            git push
+          else
+            echo "no changes"
+          fi
       - uses: actions/upload-pages-artifact@v3
         with:
           path: docs
       - id: deploy
         uses: actions/deploy-pages@v4
         continue-on-error: true
```

The split-job patch is larger and has more surface area, but it preserves the existing operational property that the Pages deploy runs on a GitHub-hosted runner where the OIDC token plumbing is most straightforward. It also reduces the work the home machine or Free-tier VM has to do per cycle: only the HTTP-bound fetch steps run on the constrained host. The fetch job's data commit triggers the build-deploy job through `needs: fetch`, and the build job checks out the latest main to pick up the data the fetch job just pushed.

### Which option to pick

The minimal one-line change is the right choice when the chosen runner host has comfortable resources, when the operator wants the simplest possible rollback path, and when the workflow's all-in-one structure is preferable for log-reading and debugging. A residential machine with reasonable specs (4+ GB of RAM, a modern processor, stable internet) is a good fit for this option. The Oracle Cloud Always Free ARM instance is also a fit because its 6 GB of RAM and 1 OCPU is sufficient even with the build step included, though the per-cycle wall-clock time will be longer than on a beefier machine.

The split-job patch is the right choice when the chosen runner host is constrained (a Raspberry Pi 3 or older, a very small ARM VM), when the operator values keeping the Pages-deploy path on a known-good GitHub-hosted runner, or when the operator anticipates that the runner host might be unreliable (a home machine that occasionally reboots) and wants the build to retry independently from the GitHub-hosted side without requiring the home machine to recover first.

For a first deployment, the minimal one-line patch is the recommended starting point because the simpler diff is easier to reason about. If operational experience shows that the host machine is undersized or that the deploy step has trouble on the self-hosted runner, the split-job patch is a straightforward second migration.

## Self-hosted runner registration

GitHub's documented self-hosted runner registration is a short sequence on the target machine. The registration token is repo-specific and short-lived (typically valid for one hour after issuance), so the operator obtains it just before running the registration command.

The token is retrieved from the JCStream repository on github.com:

  Settings → Actions → Runners → New self-hosted runner → choose OS → copy the displayed token

The token appears in the GitHub-provided shell script as the `--token` argument to `config.sh`. It is opaque to the operator; copy verbatim.

On the target machine (Linux x86_64 or ARM, depending on which the operator picked):

```bash
# Create a runner directory in the operator's home directory or a system path.
mkdir -p ~/jcstream-runner && cd ~/jcstream-runner

# Download the runner package. The URL appears in GitHub's "New self-hosted
# runner" page; the version below is a placeholder, replace with the current one.
curl -o actions-runner-linux-x64.tar.gz -L \
  https://github.com/actions/runner/releases/download/<VERSION>/actions-runner-linux-x64-<VERSION>.tar.gz

# Extract.
tar xzf actions-runner-linux-x64.tar.gz

# Configure the runner with the JCStream repo, the registration token from
# GitHub, and the label that the workflow YAML expects.
./config.sh \
  --url https://github.com/AICincy/JCStream \
  --token <REGISTRATION_TOKEN_FROM_GITHUB> \
  --labels hcso-fetch \
  --unattended \
  --replace

# Install as a system service so it survives reboots.
sudo ./svc.sh install
sudo ./svc.sh start

# Confirm the service is running.
sudo ./svc.sh status
```

The label `hcso-fetch` is the string the workflow YAML references in `runs-on: [self-hosted, hcso-fetch]`. The `self-hosted` label is implicit and always present on every self-hosted runner; the `hcso-fetch` label is specific to this runner's purpose and is what disambiguates it from any other self-hosted runners the operator might register in the future. The `--replace` flag means that if a runner with this name already exists in the repo, the new registration overwrites it, which is useful when re-registering after a machine wipe or migration.

The service-install step is what makes the runner survive a reboot. Without it, the runner stops as soon as the operator closes the SSH session. The `svc.sh` script writes a systemd unit (on systems that use systemd) and configures it to start at boot.

## Git credentials for the commit step

The workflow's commit-and-push step at the bottom of the sweep job runs `git push`, which on a GitHub-hosted runner uses the implicit `GITHUB_TOKEN` provided by Actions. That same token is available to self-hosted runners through the `${{ secrets.GITHUB_TOKEN }}` interpolation, so no separate credential configuration is required at the runner level: the workflow YAML already has access to the right token. The runner inherits the token through its workflow context, not through any persistent file on the host machine.

If for some reason the operator wants to use a fine-grained personal access token instead of the implicit `GITHUB_TOKEN` (for example, to scope the token more tightly than the default permissions), the alternative is to add a step before the existing commit step that configures git with the PAT:

```yaml
- name: Configure git with PAT
  run: |
    git remote set-url origin https://${{ secrets.JCSTREAM_PUSH_PAT }}@github.com/AICincy/JCStream.git
```

The PAT lives in repo Secrets as `JCSTREAM_PUSH_PAT`, scoped to `contents: write` on the JCStream repo only. The token is never written to disk on the runner; it is interpolated into the remote URL at step time and the URL is reset on each workflow run.

For the standard deployment, the implicit `GITHUB_TOKEN` is sufficient and the PAT path is unnecessary.

## Verification before the cron relies on the runner

Before allowing the next scheduled sweep to run on the new self-hosted runner, the operator should verify that the runner works end-to-end. Two verifications are appropriate.

The first is the runner's own self-test, which happens during `config.sh` if the registration was successful. The runner connects to GitHub, exchanges the registration token for a long-lived runner credential, and reports back. If `svc.sh status` shows the runner as active and listening, the runner-to-GitHub direction is confirmed.

The second is a manual workflow dispatch of the sweep workflow. From the JCStream repo on github.com:

  Actions → sweep → Run workflow → (leave defaults)

The dispatch should route to the self-hosted runner because the workflow now matches `[self-hosted, hcso-fetch]`. The Actions log will show the job being assigned to the named runner. The operator watches the run to completion, confirming three things:

  1. The HCSO fetch step completes with full-sized responses, indicated by absence of the "WAF-block-shaped response" warning. This confirms that the new runner's source IP is not WAF-blocked.

  2. The build step completes without resource exhaustion warnings or out-of-memory kills. This confirms that the host machine has sufficient capacity for the workflow.

  3. The Pages deploy step completes and the deploy job's environment URL shows the expected aretheyinjail.com URL. This confirms that the OIDC and deploy plumbing works from the self-hosted runner.

If all three pass, the runner is ready to take the scheduled cron. If any fail, the operator can pause the scheduled cron (by commenting out the `schedule:` block temporarily) while debugging, without affecting site availability because the previous successful build is still live on Pages.

## Rollback

If the new runner needs to be removed for any reason, the rollback is a single revert commit that restores `runs-on: ubuntu-latest` in `sweep.yml`. The self-hosted runner can stay registered on the host machine indefinitely; it simply does not receive any jobs once the workflow no longer references its label. To remove the runner cleanly:

```bash
cd ~/jcstream-runner
sudo ./svc.sh stop
sudo ./svc.sh uninstall
./config.sh remove --token <REGISTRATION_TOKEN_FROM_GITHUB>
```

The removal token is obtained the same way as the registration token, from Settings → Actions → Runners → (runner name) → Remove.
