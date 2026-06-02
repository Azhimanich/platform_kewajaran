#!/usr/bin/env python3
"""
Script Runner for Data Import
Usage: python run_import.py
"""

import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from import_data import DataImporter
import mysql.connector
from mysql.connector import Error

def check_database_exists():
    """Check if database exists, create if not"""
    config = {
        'host': 'localhost',
        'user': 'root',
        'password': ''
    }
    
    try:
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        
        # Create database if not exists
        cursor.execute("CREATE DATABASE IF NOT EXISTS kewajaran")
        cursor.execute("USE kewajaran")
        
        print("Database 'kewajaran' is ready")
        
        cursor.close()
        connection.close()
        
        return True
        
    except Error as e:
        print(f"Database setup error: {e}")
        return False

def execute_sql_structure():
    """Execute database structure SQL"""
    config = {
        'host': 'localhost',
        'user': 'root',
        'password': '',
        'database': 'kewajaran'
    }
    
    try:
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        
        # Read and execute SQL file
        with open('database_structure.sql', 'r', encoding='utf-8') as file:
            sql_commands = file.read()
            
        # Split commands and execute
        commands = sql_commands.split(';')
        for command in commands:
            if command.strip():
                cursor.execute(command)
                
        connection.commit()
        print("Database structure created successfully")
        
        cursor.close()
        connection.close()
        
        return True
        
    except Error as e:
        print(f"SQL execution error: {e}")
        return False
    except FileNotFoundError:
        print("database_structure.sql not found")
        return False

def main():
    """Main execution function"""
    print("=" * 50)
    print("PLATFORM KEWAJARAN PENGANGGARAN")
    print("Data Import Script")
    print("=" * 50)
    
    # Step 1: Check and create database
    print("\n1. Setting up database...")
    if not check_database_exists():
        print("Failed to setup database")
        return
    
    # Step 2: Create table structure
    print("\n2. Creating table structure...")
    if not execute_sql_structure():
        print("Failed to create table structure")
        return
    
    # Step 3: Import data
    print("\n3. Importing CSV data...")
    try:
        importer = DataImporter()
        importer.process_all_files()
        print("\n[OK] Data import completed successfully!")
        print("\nDatabase Summary:")
        print("- Database: kewajaran")
        print("- Tables: pemdas, skpds, nomenklaturs, usulan_anggarans, realisasi_anggarans, users")
        print("- Years: 2024-2027")
        print("- Regions: DIY + 5 Kabupaten/Kota")
        print("- Realisasi data generated for 2024-2025")
        
    except Exception as e:
        print(f" Import failed: {e}")
    finally:
        if 'importer' in locals():
            importer.disconnect_db()
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()
