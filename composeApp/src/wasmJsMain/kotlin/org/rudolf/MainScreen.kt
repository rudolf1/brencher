package org.rudolf

import androidx.compose.runtime.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.*
import androidx.compose.material.*
import androidx.compose.material3.*
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import dto.*

@Composable
fun MainScreen() {
    var repoUrl by remember { mutableStateOf("") }
    var branches by remember { mutableStateOf(listOf<String>()) }
    var releases by remember { mutableStateOf(listOf<ReleaseDto>()) }
    var environments by remember { mutableStateOf(listOf<EnvironmentDto>()) }
    var newReleaseName by remember { mutableStateOf("") }
    var newEnvironmentName by remember { mutableStateOf("") }
    var newEnvironmentConfig by remember { mutableStateOf("{}") }
    var selectedBranches by remember { mutableStateOf(setOf<String>()) }
    var selectedEnvironment by remember { mutableStateOf("") }
    var releaseState by remember { mutableStateOf(ReleaseState.PAUSE) }

    // Load data on component mount
    LaunchedEffect(Unit) {
        environments = fetchEnvironments()
        releases = fetchReleases()
    }

    Column(modifier = Modifier.padding(16.dp)) {
        // Repository Section
        Text("Git Repository", style = MaterialTheme.typography.headlineMedium)
        TextField(
            value = repoUrl,
            onValueChange = { repoUrl = it },
            label = { Text("Repository URL") },
            modifier = Modifier.fillMaxWidth()
        )
        Button(
            onClick = {
                CoroutineScope(Dispatchers.Default).launch {
                    branches = fetchBranches(repoUrl)
                }
            },
            modifier = Modifier.padding(vertical = 8.dp)
        ) {
            Text("Fetch Branches")
        }

        // Environments Section
        Text("EnvironmentsXXX", style = MaterialTheme.typography.headlineMedium)
        Row(modifier = Modifier.padding(vertical = 8.dp)) {
            TextField(
                value = newEnvironmentName,
                onValueChange = { newEnvironmentName = it },
                label = { Text("Environment Name") },
                modifier = Modifier.weight(1f)
            )
            Spacer(Modifier.width(8.dp))
            TextField(
                value = newEnvironmentConfig,
                onValueChange = { newEnvironmentConfig = it },
                label = { Text("Configuration (JSON)") },
                modifier = Modifier.weight(1f)
            )
            Spacer(Modifier.width(8.dp))
            Button(
                onClick = {
                    CoroutineScope(Dispatchers.Default).launch {
                        createEnvironment(EnvironmentDto(
                            name = newEnvironmentName,
                            configuration = newEnvironmentConfig
                        ))
                        environments = fetchEnvironments()
                        newEnvironmentName = ""
                        newEnvironmentConfig = "{}"
                    }
                },
                enabled = newEnvironmentName.isNotBlank()
            ) {
                Text("Add Environment")
            }
        }

        environments.forEach { environment ->
            Card(
                modifier = Modifier.padding(vertical = 8.dp).fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Name: ${environment.name}")
                    Text("Configuration:")
                    Text(environment.configuration)
                    Row(
                        modifier = Modifier.padding(top = 8.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Button(
                            onClick = {
                                CoroutineScope(Dispatchers.Default).launch {
                                    deleteEnvironment(environment.name)
                                    environments = fetchEnvironments()
                                }
                            }
                        ) {
                            Text("Delete")
                        }
                    }
                }
            }
        }

        // Branches Section
        if (branches.isNotEmpty()) {
            Text("Branches", style = MaterialTheme.typography.headlineMedium)
            branches.forEach { branch ->
                Row(
                    modifier = Modifier.padding(vertical = 4.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Checkbox(
                        checked = selectedBranches.contains(branch),
                        onCheckedChange = { checked ->
                            selectedBranches = if (checked) {
                                selectedBranches + branch
                            } else {
                                selectedBranches - branch
                            }
                        }
                    )
                    Text(branch)
                }
            }
        }

        // Releases Section
        Text("Releases", style = MaterialTheme.typography.headlineMedium)
        Row(modifier = Modifier.padding(vertical = 8.dp)) {
            TextField(
                value = newReleaseName,
                onValueChange = { newReleaseName = it },
                label = { Text("Release Name") }
            )
            Spacer(Modifier.width(8.dp))
            Button(
                onClick = {
                    CoroutineScope(Dispatchers.Default).launch {
                        createRelease(ReleaseDto(
                            name = newReleaseName,
                            branches = selectedBranches.toList(),
                            state = releaseState,
                            environment = selectedEnvironment
                        ))
                        releases = fetchReleases()
                        newReleaseName = ""
                        selectedBranches = emptySet()
                    }
                },
                enabled = newReleaseName.isNotBlank() && selectedBranches.isNotEmpty()
            ) {
                Text("Create Release")
            }
        }

        releases.forEach { release ->
            Card(
                modifier = Modifier.padding(vertical = 8.dp).fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Release: ${release.name}")
                    Text("State: ${release.state}")
                    Text("Environment: ${release.environment}")
                    Text("Branches:")
                    release.branches.forEach { branch ->
                        Text("• $branch")
                    }
                    Row(
                        modifier = Modifier.padding(top = 8.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Button(
                            onClick = {
                                CoroutineScope(Dispatchers.Default).launch {
                                    deleteRelease(release.name)
                                    releases = fetchReleases()
                                }
                            }
                        ) {
                            Text("Delete")
                        }
                        Button(
                            onClick = {
                                CoroutineScope(Dispatchers.Default).launch {
                                    updateReleaseState(
                                        release.name,
                                        if (release.state == ReleaseState.ACTIVE) ReleaseState.PAUSE else ReleaseState.ACTIVE
                                    )
                                    releases = fetchReleases()
                                }
                            }
                        ) {
                            Text(if (release.state == ReleaseState.ACTIVE) "Pause" else "Activate")
                        }
                    }
                }
            }
        }
    }
}

