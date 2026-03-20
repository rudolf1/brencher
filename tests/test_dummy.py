# # pytest --inline-snapshot=fix.

# def test_dummy() -> None:
# 	assert True

# from inline_snapshot import snapshot


# from dirty_equals import IsInt, IsNow
# from pydantic import TypeAdapter

# _adapter = TypeAdapter(object)

# def test1():
# 	data = fetch_data()

# 	assert user_data == snapshot({
# 		"id": IsInt(),          # Снепшот запомнит условие, а не число
# 		"created_at": IsNow(),  # Проверит время, близкое к текущему
# 		"status": "active"
# 	})
