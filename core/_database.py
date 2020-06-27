"""This module handles reading from and writing to the ShootPoints database."""

import sqlite3
import os


dbconn = sqlite3.connect('ShootPoints.db', check_same_thread=False)
dbconn.row_factory = sqlite3.Row
cursor = dbconn.cursor()
try:
    cursor.execute('SELECT 1 FROM stations')
except:
    # ShootPoints.db database is empty, so initialize it with the default schema.
    with open('blank_database.sql', 'r') as f:
        sql = f.read().split(';')
        _ = [cursor.execute(query) for query in sql]
        dbconn.commit()


def save_to_database(sql: str, data: tuple) -> dict:
    """This function performs an INSERT or UPDATE of the given data using the provided query string."""
    outcome = {'errors': [], 'result': ''}
    if sql[:11].upper().find('INSERT INTO') == 0 or sql[:6].upper().find('UPDATE') == 0:
        try:
            cursor.execute(sql, data)
            dbconn.commit()
            outcome['result'] = 'Data successfully saved to the database.'
        except sqlite3.Error as err:
            outcome['errors'].append(str(err))
    else:
        outcome['errors'].append('The given sql does not appear to be an INSERT or UPDATE query.')
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if val or key == 'success'}


def read_from_database(sql: str, params: tuple=()) -> dict:
    """This function performs a SELECT query on the database, with optional parameters."""
    outcome = {'errors': [], 'results': []}
    if sql[:6].upper().find('SELECT') == 0:
        try:
            cursor.execute(sql, params)
            outcome['results'].append([dict(row) for row in cursor.fetchall()])
        except sqlite3.Error as err:
            outcome['errors'].append(str(err))
    else:
        outcome['errors'].append('The given sql does not appear to be a SELECT query.')
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if val or key == 'success'}


def _record_setup_error(error: str) -> None:
    sql = 'INSERT INTO setuperrors (error) VALUES (?)'
    try:
        cursor.execute(sql, (error,))
        dbconn.commit()
    except sqlite3.IntegrityError:
        pass


def _clear_setup_errors() -> None:
    try:
        cursor.execute('DELETE FROM setuperrors')
        dbconn.commit()
    except:
        pass
