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











rencher_brencher-backend.1.or9sbknhh4zt@odroid    |   File "/app/.venv/lib/python3.12/site-packages/socketio/server.py", line 656, in _handle_eio_message
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |     self._handle_connect(eio_sid, pkt.namespace, pkt.data)
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |   File "/app/.venv/lib/python3.12/site-packages/socketio/server.py", line 539, in _handle_connect
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |     success = self._trigger_event(
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |               ^^^^^^^^^^^^^^^^^^^^
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |   File "/app/.venv/lib/python3.12/site-packages/socketio/server.py", line 631, in _trigger_event
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |     return handler.trigger_event(event, *args)
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |   File "/app/.venv/lib/python3.12/site-packages/flask_socketio/namespace.py", line 26, in trigger_event
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |     return self.socketio._handle_event(handler, event, self.namespace,
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |   File "/app/.venv/lib/python3.12/site-packages/flask_socketio/__init__.py", line 854, in _handle_event
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |     ret = handler(auth)
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |           ^^^^^^^^^^^^^
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |   File "/app/backend/app.py", line 182, in on_connect
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |     emit('environments', get_global_envs_to_emit())
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |                          ^^^^^^^^^^^^^^^^^^^^^^^^^
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |   File "/app/backend/app.py", line 164, in get_global_envs_to_emit
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |     local_envs = get_local_envs_to_emit()
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |                  ^^^^^^^^^^^^^^^^^^^^^^^^
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |   File "/app/backend/app.py", line 148, in get_local_envs_to_emit
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |     if isinstance(r.progress(), BaseException):
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |                  ^^^^^^^^^^^^
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |   File "/app/backend/steps/step.py", line 28, in progress
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |     raise self._result
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |   File "/app/backend/app.py", line 116, in _remote_environments
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |     socketio.emit('environments', get_global_envs_to_emit(), namespace='/ws/environment')
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |                                   ^^^^^^^^^^^^^^^^^^^^^^^^^
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |   File "/app/backend/app.py", line 164, in get_global_envs_to_emit
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |     local_envs = get_local_envs_to_emit()
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |                  ^^^^^^^^^^^^^^^^^^^^^^^^
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |   File "/app/backend/app.py", line 148, in get_local_envs_to_emit
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |     if isinstance(r.progress(), BaseException):
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |                  ^^^^^^^^^^^^
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |   File "/app/backend/steps/step.py", line 28, in progress
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |     raise self._result
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |   File "/app/backend/steps/step.py", line 23, in progress
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |     self._result = self.step.progress()
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |                    ^^^^^^^^^^^^^^^^^^^^
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |   File "/app/backend/steps/git.py", line 41, in progress
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |     result = repo.remotes.origin.fetch(prune=True)
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |   File "/app/.venv/lib/python3.12/site-packages/git/remote.py", line 1076, in fetch
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |     res = self._get_fetch_info_from_stderr(proc, progress, kill_after_timeout=kill_after_timeout)
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |   File "/app/.venv/lib/python3.12/site-packages/git/remote.py", line 902, in _get_fetch_info_from_stderr
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |     proc.wait(stderr=stderr_text)
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |   File "/app/.venv/lib/python3.12/site-packages/git/cmd.py", line 419, in wait
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |     raise GitCommandError(remove_password_if_present(self.args), status, errstr)
brencher_brencher-backend.1.or9sbknhh4zt@odroid    | git.exc.GitCommandError: Cmd('git') failed due to: exit code(1)
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |   cmdline: git fetch -v --prune -- origin
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |   stderr: 'error: cannot lock ref 'refs/remotes/origin/unmerge_asserts': is at dd514e690cc6d6b8fb266ca6c61d7f8d0242164c but expected a28dd6c8cfc34f9c6aeda03fec89eec7bc5db7f2'
brencher_brencher-backend.1.or9sbknhh4zt@odroid    | 2026-02-27 23:38:36,623 - __main__ - ERROR - Error forwarding remote environments locally: Cmd('git') failed due to: exit code(1)
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |   cmdline: git fetch -v --prune -- origin
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |   stderr: 'error: cannot lock ref 'refs/remotes/origin/unmerge_asserts': is at dd514e690cc6d6b8fb266ca6c61d7f8d0242164c but expected a28dd6c8cfc34f9c6aeda03fec89eec7bc5db7f2'
brencher_brencher-backend.1.or9sbknhh4zt@odroid    | 2026-02-27 23:38:36,633 - __main__ - ERROR - Error forwarding remote environments locally: Cmd('git') failed due to: exit code(1)
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |   cmdline: git fetch -v --prune -- origin
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |   stderr: 'error: cannot lock ref 'refs/remotes/origin/unmerge_asserts': is at dd514e690cc6d6b8fb266ca6c61d7f8d0242164c but expected a28dd6c8cfc34f9c6aeda03fec89eec7bc5db7f2'
brencher_brencher-backend.1.or9sbknhh4zt@odroid    | 2026-02-27 23:38:36,639 - __main__ - ERROR - Error forwarding remote environments locally: Cmd('git') failed due to: exit code(1)
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |   cmdline: git fetch -v --prune -- origin
brencher_brencher-backend.1.or9sbknhh4zt@odroid    |   stderr: 'error: cannot lock ref 'refs/remotes/origin/unmerge_asserts': is at dd514e690cc6d6b8fb266ca6c61d7f8d0242164c but expected a28dd6c8cfc34f9c6aeda03fec89eec7bc5db7f2'

