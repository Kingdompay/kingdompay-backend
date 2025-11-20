#!/usr/bin/env python3
"""
View PostgreSQL Tables
Simple script to list and view tables in the database
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from sqlalchemy import text, inspect

def list_tables(app):
    """List all tables in the database"""
    with app.app_context():
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        print("\n" + "=" * 60)
        print("PostgreSQL Tables")
        print("=" * 60)
        print(f"\nTotal tables: {len(tables)}\n")
        
        # Group tables for better display
        table_data = []
        for i, table in enumerate(sorted(tables), 1):
            try:
                # Get row count
                result = db.session.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                row_count = result.scalar()
                table_data.append([i, table, row_count])
            except Exception:
                table_data.append([i, table, "N/A"])
        
        # Print table
        print(f"{'#':<5} {'Table Name':<30} {'Row Count':<15}")
        print("-" * 60)
        for row in table_data:
            print(f"{row[0]:<5} {row[1]:<30} {row[2]:<15}")
        return tables

def view_table_structure(app, table_name):
    """View structure of a specific table"""
    with app.app_context():
        inspector = inspect(db.engine)
        
        if table_name not in inspector.get_table_names():
            print(f"\n✗ Table '{table_name}' does not exist")
            return
        
        print(f"\n{'=' * 60}")
        print(f"Table: {table_name}")
        print("=" * 60)
        
        # Get columns
        columns = inspector.get_columns(table_name)
        column_data = []
        for col in columns:
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            default = f"DEFAULT {col['default']}" if col['default'] else ""
            column_data.append([
                col['name'],
                str(col['type']),
                nullable,
                default
            ])
        
        print("\nColumns:")
        print(f"{'Column':<25} {'Type':<30} {'Nullable':<15} {'Default':<20}")
        print("-" * 90)
        for row in column_data:
            print(f"{row[0]:<25} {str(row[1]):<30} {row[2]:<15} {str(row[3]):<20}")
        
        # Get indexes
        indexes = inspector.get_indexes(table_name)
        if indexes:
            print("\nIndexes:")
            print(f"{'Index':<30} {'Columns':<40} {'Type':<10}")
            print("-" * 80)
            for idx in indexes:
                idx_type = 'UNIQUE' if idx['unique'] else ''
                print(f"{idx['name']:<30} {', '.join(idx['column_names']):<40} {idx_type:<10}")
        
        # Get foreign keys
        foreign_keys = inspector.get_foreign_keys(table_name)
        if foreign_keys:
            print("\nForeign Keys:")
            print(f"{'FK Name':<30} {'Columns':<30} {'References':<40}")
            print("-" * 100)
            for fk in foreign_keys:
                print(f"{fk['name'] or 'N/A':<30} {', '.join(fk['constrained_columns']):<30} {fk['referred_table']}.{', '.join(fk['referred_columns']):<40}")

def view_table_data(app, table_name, limit=10):
    """View data from a specific table"""
    with app.app_context():
        inspector = inspect(db.engine)
        
        if table_name not in inspector.get_table_names():
            print(f"\n✗ Table '{table_name}' does not exist")
            return
        
        print(f"\n{'=' * 60}")
        print(f"Table Data: {table_name} (showing first {limit} rows)")
        print("=" * 60)
        
        try:
            # Get data
            result = db.session.execute(text(f'SELECT * FROM "{table_name}" LIMIT {limit}'))
            rows = result.fetchall()
            
            if not rows:
                print("\n(No data)")
                return
            
            # Get column names from first row keys or result keys
            if hasattr(result, 'keys'):
                columns = list(result.keys())
            elif rows:
                # Fallback: get from row keys if it's a Row object
                columns = list(rows[0]._fields) if hasattr(rows[0], '_fields') else [f'col_{i}' for i in range(len(rows[0]))]
            else:
                columns = []
            
            # Convert rows to list of lists
            table_data = [list(row) if hasattr(row, '__iter__') and not isinstance(row, str) else [row] for row in rows]
            
            # Truncate long values for display
            for row in table_data:
                for i, val in enumerate(row):
                    if val is not None and len(str(val)) > 50:
                        row[i] = str(val)[:47] + "..."
            
            # Print table with headers
            # Calculate column widths
            col_widths = [len(str(col)) for col in columns]
            for row in table_data:
                for i, val in enumerate(row):
                    if i < len(col_widths):
                        col_widths[i] = max(col_widths[i], len(str(val)) if val else 0)
            
            # Print header
            header_row = " | ".join(str(col).ljust(col_widths[i]) for i, col in enumerate(columns))
            print(f"\n{header_row}")
            print("-" * len(header_row))
            
            # Print data rows
            for row in table_data:
                data_row = " | ".join(str(val).ljust(col_widths[i]) if val is not None else "NULL".ljust(col_widths[i]) 
                                    for i, val in enumerate(row))
                print(data_row)
            
            # Get total count
            count_result = db.session.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
            total = count_result.scalar()
            if total > limit:
                print(f"\n... and {total - limit} more rows (total: {total})")
            
        except Exception as e:
            print(f"\n✗ Error viewing table data: {e}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="View PostgreSQL tables")
    parser.add_argument('table', nargs='?', help='Table name to view (optional)')
    parser.add_argument('--structure', '-s', action='store_true', help='Show table structure')
    parser.add_argument('--data', '-d', action='store_true', help='Show table data')
    parser.add_argument('--limit', '-l', type=int, default=10, help='Limit rows when showing data (default: 10)')
    
    args = parser.parse_args()
    
    # Check DATABASE_URL
    if not os.environ.get("DATABASE_URL"):
        print("⚠ DATABASE_URL not set. Using default SQLite.")
        print("To view PostgreSQL tables, set:")
        print("  export DATABASE_URL='postgresql://admin:admin123@localhost:5433/kingdompay'")
    
    app = create_app()
    
    # List all tables if no table specified
    if not args.table:
        list_tables(app)
        print("\nUsage:")
        print("  python3 scripts/view_tables.py <table_name> --structure  # View table structure")
        print("  python3 scripts/view_tables.py <table_name> --data       # View table data")
        print("  python3 scripts/view_tables.py <table_name> -s -d        # View both")
        return
    
    # View specific table
    table_name = args.table
    
    if args.structure:
        view_table_structure(app, table_name)
    
    if args.data:
        view_table_data(app, table_name, args.limit)
    
    if not args.structure and not args.data:
        # Default: show structure and data
        view_table_structure(app, table_name)
        view_table_data(app, table_name, args.limit)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

