# Concrete and Steel Calculator for Slabs
# Saves results in Arabic inside a text file

# User input
length = float(input("Enter the slab length (meters): "))
width = float(input("Enter the slab width (meters): "))
thickness = float(input("Enter the slab thickness (meters): "))

# Concrete volume calculation
concrete_volume = length * width * thickness  # cubic meters

# Steel weight calculation
steel_rate = 100  # kg of steel per 1 cubic meter of concrete
steel_weight = concrete_volume * steel_rate  # total steel weight in kg

# Save results in Arabic inside a text file
with open("results.txt", "w", encoding="utf-8") as file:
    file.write("=== نتائج حساب السقف ===\n")
    file.write(f"طول السقف: {length} متر\n")
    file.write(f"عرض السقف: {width} متر\n")
    file.write(f"سماكة السقف: {thickness} متر\n\n")
    file.write(f"حجم الخرسانة المطلوب: {concrete_volume:.2f} متر مكعب\n")
    file.write(f"وزن حديد التسليح التقريبي: {steel_weight:.2f} كغم\n")

# Notify user
print("\nResults saved successfully in 'results.txt' ✅")