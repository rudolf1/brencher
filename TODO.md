# ! brencher - CheckoutMerged
# [
#   "Cmd('git') failed due to: exit code(1)\n  cmdline: git branch -D auto/c51670b7394353f68332989d75f03e8b9792d7b7\n  stderr: 'error: cannot delete branch 'auto/c51670b7394353f68332989d75f03e8b9792d7b7' used by worktree at '/tmp/brencher_d4d5a''",
#   [
#     "Traceback (most recent call last):\n",
#     "  File \"/app/backend/processing.py\", line 17, in process_all_jobs\n    step.result\n",
#     "  File \"/app/backend/steps/step.py\", line 44, in result\n    raise self._result\n",
#     "  File \"/app/backend/steps/step.py\", line 39, in result\n    self._result = self.progress()\n                   ^^^^^^^^^^^^^^^\n",
#     "  File \"/app/backend/steps/docker.py\", line 152, in progress\n    if self.buildDocker is not None and isinstance(self.buildDocker.result, BaseException):\n                                                   ^^^^^^^^^^^^^^^^^^^^^^^\n",
#     "  File \"/app/backend/steps/step.py\", line 44, in result\n    raise self._result\n",
#     "  File \"/app/backend/processing.py\", line 17, in process_all_jobs\n    step.result\n",
#     "  File \"/app/backend/steps/step.py\", line 44, in result\n    raise self._result\n",
#     "  File \"/app/backend/steps/step.py\", line 39, in result\n    self._result = self.progress()\n                   ^^^^^^^^^^^^^^^\n",
#     "  File \"/app/backend/steps/docker.py\", line 91, in progress\n    raise e\n",
#     "  File \"/app/backend/steps/docker.py\", line 48, in progress\n    env = self.envs()\n          ^^^^^^^^^^^\n",
#     "  File \"/app/backend/configs/brencher.py\", line 32, in \n    \"version\": \"auto-\" + checkoutMerged.result.version,\n                         ^^^^^^^^^^^^^^^^^^^^^\n",
#     "  File \"/app/backend/steps/step.py\", line 44, in result\n    raise self._result\n",
#     "  File \"/app/backend/processing.py\", line 17, in process_all_jobs\n    step.result\n",
#     "  File \"/app/backend/steps/step.py\", line 44, in result\n    raise self._result\n",
#     "  File \"/app/backend/steps/step.py\", line 39, in result\n    self._result = self.progress()\n                   ^^^^^^^^^^^^^^^\n",
#     "  File \"/app/backend/steps/git.py\", line 202, in progress\n    repo.git.branch('-D', auto_branch_name)\n",
#     "  File \"/app/.venv/lib/python3.12/site-packages/git/cmd.py\", line 1003, in \n    return lambda *args, **kwargs: self._call_process(name, *args, **kwargs)\n                                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
#     "  File \"/app/.venv/lib/python3.12/site-packages/git/cmd.py\", line 1616, in _call_process\n    return self.execute(call, **exec_kwargs)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
#     "  File \"/app/.venv/lib/python3.12/site-packages/git/cmd.py\", line 1406, in execute\n    raise GitCommandError(redacted_command, status, stderr_value, stdout_value)\n",
#     "git.exc.GitCommandError: Cmd('git') failed due to: exit code(1)\n  cmdline: git branch -D auto/c51670b7394353f68332989d75f03e8b9792d7b7\n  stderr: 'error: cannot delete branch 'auto/c51670b7394353f68332989d75f03e8b9792d7b7' used by worktree at '/tmp/brencher_d4d5a''\n"
#   ]
# ]