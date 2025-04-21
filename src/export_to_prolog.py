import sqlite3

def export_to_prolog(db_path, output_file):
    """Export medicines database to a Prolog knowledge base."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query all medicines
    cursor.execute("SELECT name, brand, price, dosage, form, otc, description, side_effects, category FROM medicines")
    rows = cursor.fetchall()

    with open(output_file, "w") as f:
        f.write("% Prolog knowledge base for medicines\n")
        for row in rows:
            name, brand, price, dosage, form, otc, description, side_effects, category = row
            prolog_fact = f"medicine('{name}', '{brand}', {price}, '{dosage}', '{form}', {str(bool(otc)).lower()}, '{description}', '{side_effects}', '{category}').\n"
            f.write(prolog_fact)

    conn.close()
    print(f"Prolog knowledge base exported to {output_file}")

# Example usage
if __name__ == "__main__":
    export_to_prolog("medicine.db", "medicines.pl")
    