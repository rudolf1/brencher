package org.rudolf.routes

import kotlinx.coroutines.runBlocking
import org.eclipse.jgit.api.Git
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import kotlin.io.path.createTempDirectory

/**
 * Unit test for class GitService.
 *
 * - Create local git repo.
 * - Create 2 branches based on same commit and non conflicting for merge.
 * - Execute mergeBranchesAndPushAutoBranch for these branches.
 * - Result should be successfull
 */
class GitServiceTest {
    @Test
    fun `mergeBranchesAndPushAutoBranch merges non-conflicting branches successfully`() = runBlocking {
        // Create a temp directory for the test repo
        val tempDir = createTempDirectory("test-git-repo").toFile()
        val git = Git.init().setDirectory(tempDir).call()
        // Create initial file and commit
        val file = File(tempDir, "file.txt")
        file.writeText("base\n")
        git.add().addFilepattern("file.txt").call()
        git.commit().setMessage("initial commit").call()
        // Create branch1 and add a line
        git.branchCreate().setName("branch1").call()
        git.checkout().setName("branch1").call()
        file.appendText("branch1\n")
        git.add().addFilepattern("file.txt").call()
        git.commit().setMessage("branch1 commit").call()
        // Create branch2 from master and add a line
        git.checkout().setName("master").call()
        git.branchCreate().setName("branch2").call()
        git.checkout().setName("branch2").call()
        file.appendText("branch2\n")
        git.add().addFilepattern("file.txt").call()
        git.commit().setMessage("branch2 commit").call()
        // Now test mergeBranchesAndPushAutoBranch
        // Simulate GitService configured to use this repo
        org.rudolf.GitService.configure(tempDir.absolutePath, 5)
        val result = org.rudolf.GitService.mergeBranchesAndPushAutoBranch(listOf("branch1", "branch2"))
        assertTrue(result.isSuccess)
        result.onFailure { println(it.message) }
        val autoBranch = result.getOrNull()
        assertTrue(autoBranch != null && autoBranch.startsWith("auto/"))
    }
}
