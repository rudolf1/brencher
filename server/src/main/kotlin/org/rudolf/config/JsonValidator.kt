package org.rudolf.config

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement

object JsonValidator {
    private val json = Json { prettyPrint = true }

    fun isValidJson(jsonString: String): Boolean {
        return try {
            json.parseToJsonElement(jsonString)
            true
        } catch (e: Exception) {
            false
        }
    }

    fun formatJson(jsonString: String): String {
        val element = json.parseToJsonElement(jsonString)
        return json.encodeToString(JsonElement.serializer(), element)
    }
}
