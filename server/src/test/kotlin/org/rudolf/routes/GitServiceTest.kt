package org.rudolf.routes

import org.rudolf.GitService
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.runBlocking
import kotlin.test.*
import java.io.File
import org.eclipse.jgit.api.Git

/**
Unit test for class GitService.

- Create local git repo as original git repo.
- Point git service to this repo.
- Create 2 branches based on same commit and non conflicting for merge.
- Execute mergeBranchesAndPushAutoBranch for these branches.
- Result should be successfull
 */
@OptIn(ExperimentalCoroutinesApi::class)
class GitServiceTest {
    @Test
    fun mergeBranchesAndPushAutoBranch_mergesNonConflictingBranchesSuccessfully() = runBlocking {
        // 1. Create a local git repo as the original repo
        val repoDir = File.createTempFile("test-git-repo", "").apply { delete(); mkdir() }
        val git = Git.init().setDirectory(repoDir).call()
        val file = File(repoDir, "file.txt")
        file.writeText("base\n")
        git.add().addFilepattern("file.txt").call()
        git.commit().setMessage("Initial commit").call()

        // 2. Create two branches from the same commit
        val branch1 = "feature/one"
        val branch2 = "feature/two"
        git.branchCreate().setName(branch1).call()
        git.branchCreate().setName(branch2).call()

        // 3. Make non-conflicting changes in each branch
        git.checkout().setName(branch1).call()
        file.appendText("change one\n")
        git.add().addFilepattern("file.txt").call()
        git.commit().setMessage("Change one").call()

        git.checkout().setName(branch2).call()
        file.appendText("change two\n")
        git.add().addFilepattern("file.txt").call()
        git.commit().setMessage("Change two").call()

        // 4. Point GitService to this repo
        GitService.configure(repoDir.toURI().toString(), 5)

        // 5. Execute mergeBranchesAndPushAutoBranch for these branches
        val result = GitService.mergeBranchesAndPushAutoBranch(listOf(branch1, branch2))
        assertTrue(result.isSuccess, "Merge should be successful: ${result.exceptionOrNull()?.message}")
        assertTrue(result.getOrNull()?.startsWith("auto/") == true, "Auto branch should be created")
    }
}
