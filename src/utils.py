import os
import sqlite3
import pandas as pd
from datetime import datetime
from src.models import Medicine, MedicineDatabase, MedicineInsight


def initialize_database():
    """Initialize the SQLite database with necessary tables if they don't exist."""
    conn = sqlite3.connect('medicine.db')
    cursor = conn.cursor()
    
    # Create medicines table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS medicines (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        brand TEXT NOT NULL,
        price REAL NOT NULL,
        dosage TEXT NOT NULL,
        form TEXT NOT NULL,
        otc INTEGER NOT NULL,
        description TEXT NOT NULL,
        side_effects TEXT NOT NULL,
        category TEXT NOT NULL,
        date_added TEXT NOT NULL
    )
    ''')
    
    # Create insights table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS insights (
        id INTEGER PRIMARY KEY,
        insight TEXT NOT NULL,
        category TEXT NOT NULL,
        date_created TEXT NOT NULL
    )
    ''')
    
    conn.commit()
    conn.close()


def add_medicine(medicine: Medicine):
    """Add a medicine to the database."""
    conn = sqlite3.connect('medicine.db')
    cursor = conn.cursor()
    
    cursor.execute(
        '''
        INSERT INTO medicines 
        (name, brand, price, dosage, form, otc, description, side_effects, category, date_added) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            medicine.name,
            medicine.brand,
            medicine.price,
            medicine.dosage,
            medicine.form,
            1 if medicine.otc else 0,
            medicine.description,
            medicine.side_effects,
            medicine.category,
            medicine.date_added
        )
    )
    
    conn.commit()
    conn.close()


def get_all_medicines() -> MedicineDatabase:
    """Retrieve all medicines from the database."""
    conn = sqlite3.connect('medicine.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM medicines')
    rows = cursor.fetchall()
    
    medicines = []
    for row in rows:
        medicines.append(
            Medicine(
                name=row['name'],
                brand=row['brand'],
                price=row['price'],
                dosage=row['dosage'],
                form=row['form'],
                otc=bool(row['otc']),
                description=row['description'],
                side_effects=row['side_effects'],
                category=row['category'],
                date_added=row['date_added']
            )
        )
    
    conn.close()
    return MedicineDatabase(medicines=medicines)


def add_insight(insight: MedicineInsight):
    """Add an insight to the database."""
    conn = sqlite3.connect('medicine.db')
    cursor = conn.cursor()
    
    cursor.execute(
        'INSERT INTO insights (insight, category, date_created) VALUES (?, ?, ?)',
        (insight.insight, insight.category, insight.date_created)
    )
    
    conn.commit()
    conn.close()


def get_all_insights() -> list:
    """Retrieve all insights from the database."""
    conn = sqlite3.connect('medicine.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM insights')
    rows = cursor.fetchall()
    
    insights = []
    for row in rows:
        insights.append(
            MedicineInsight(
                insight=row['insight'],
                category=row['category'],
                date_created=row['date_created']
            )
        )
    
    conn.close()
    return insights


def export_to_csv():
    """Export all medicines to a CSV file."""
    medicines = get_all_medicines()
    if medicines.medicines:
        df = pd.DataFrame([medicine.model_dump() for medicine in medicines.medicines])
        output_dir = os.getcwd()

        csv_path = os.path.join(output_dir, "medicines.csv")
        df.to_csv(csv_path, index=False)
        return csv_path
    return None
