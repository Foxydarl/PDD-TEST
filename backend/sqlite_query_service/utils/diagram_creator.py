import sqlite3
import pydot

def generate_er_diagram(database_file):
    # Step 1: Connect to the SQLite Database
    conn = sqlite3.connect(database_file)

    # Step 2: Extract Table Information
    cursor = conn.cursor()

    # Retrieve table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    # Retrieve columns and foreign keys for each table
    table_info = {}
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table[0]});")
        columns = cursor.fetchall()

        cursor.execute(f"PRAGMA foreign_key_list({table[0]});")
        foreign_keys = cursor.fetchall()

        table_info[table[0]] = (columns, foreign_keys)

    # Step 4: Create the ER Diagram
    graph = pydot.Dot(graph_type='graph', rankdir='LR')  # Set rankdir to 'LR' for left-to-right layout

    for table, (columns, foreign_keys) in table_info.items():
        node = pydot.Node(table, shape='record')

        # Create the label for the table node
        label = f'{{ {table} | {{'
        for column in columns:
            column_name = column[1]
            label += f' {column_name} : {column[2]}\\l'
        label += '} }}'

        node.set_label(label)
        graph.add_node(node)

        # Add relationship arrows
        for foreign_key in foreign_keys:
            source_table = table
            source_column = foreign_key[3]
            target_table = foreign_key[2]
            target_column = foreign_key[4]

            if source_table < target_table:
                arrowhead = 'crow'  # Arrow points to the target table
            else:
                arrowhead = 'tee'  # Arrow points away from the target table

            edge = pydot.Edge(f"{source_table}:{source_column}", f"{target_table}:{target_column}", arrowhead=arrowhead)
            graph.add_edge(edge)

    return graph.create(format='png')