package dto

import kotlinx.serialization.Serializable

@Serializable
enum class ReleaseState {
    PAUSE, ACTIVE
}

@Serializable
sealed class SimpleResult<out T> {
    @Serializable
    data class Success<T>(val value: T) : SimpleResult<T>()
    @Serializable
    data class Failure(val error: String) : SimpleResult<Nothing>()

    companion object {
        fun <T> fromResult(result: Result<T>): SimpleResult<T> =
            result.fold(
                onSuccess = { Success(it) },
                onFailure = { Failure(it.message ?: "Unknown error") }
            )
    }
}

@Serializable
data class ReleaseDto(
    val name: String,
    val state: ReleaseState,
    val environment: String,
    val branches: List<String>,
    val mergedBranch: SimpleResult<Pair<String, String>>? = null
)