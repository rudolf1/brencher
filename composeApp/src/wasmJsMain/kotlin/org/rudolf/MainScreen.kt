package org.rudolf

import androidx.compose.runtime.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.*
import androidx.compose.material.*
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.*
import androidx.compose.ui.Modifier

@Composable
fun MainScreen() {
    var repoUrl by remember { mutableStateOf("") }
    var branches by remember { mutableStateOf(listOf<String>()) }
    var releases by remember { mutableStateOf(listOf<Release>()) }
    var newReleaseName by remember { mutableStateOf("") }

    Column(modifier = Modifier.padding(16.dp)) {
        TextField(
            value = repoUrl,
            onValueChange = { repoUrl = it },
            label = { Text("Repository URL") }
        )
        Button(onClick = {
            CoroutineScope(Dispatchers.Default).launch {
                branches = fetchBranches(repoUrl)
            }
        }) {
            Text("Fetch Branches")
        }
        branches.forEach { branch ->
            Row {
                Checkbox(checked = false, onCheckedChange = {})
                Text(branch)
            }
        }
        TextField(
            value = newReleaseName,
            onValueChange = { newReleaseName = it },
            label = { Text("New Release Name") }
        )
        Button(onClick = {
            CoroutineScope(Dispatchers.Default).launch {
                createRelease(newReleaseName, branches)
                releases = fetchReleases()
            }
        }) {
            Text("Create Release")
        }
        releases.forEach { release ->
            Text("Release: ${release.name}")
        }
    }
}

val releases = mutableListOf<Release>(Release("test", listOf("main", "dev")))

suspend fun fetchBranches(repoUrl: String): List<String> {
    // Implement API call to fetch branches
    return listOf()
}

suspend fun fetchReleases(): List<Release> {
    // Implement API call to fetch releases
    return releases
}

suspend fun createRelease(name: String, branches: List<String>) {
    releases.add(Release(name, branches))
}

data class Release(val name: String, val branches: List<String>)