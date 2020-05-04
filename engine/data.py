"""This module handles reading from and writing to the ShootPoints database."""

import sqlite3
import os
import math


dbconn = sqlite3.connect('ShootPoints.db')
dbconn.row_factory = sqlite3.Row
cursor = dbconn.cursor()
try:
    cursor.execute('SELECT 1 FROM stations')
except:
    # The ShootPoints.db database is empty, so initialize it with the default schema.
    with open('blank_database.sql', 'r') as f:
        sql = f.read().split(';')
        _ = [cursor.execute(query) for query in sql]
        dbconn.commit()


def save_to_database(sql: str, data: tuple) -> dict:
    """This function performs an INSERT of the given data using the provided query string."""
    errors = []
    if sql[:11].upper().find('SELECT INTO') == 0:
        try:
            cursor.execute(sql, data)
            dbconn.commit()
        except sqlite3.Error as err:
            errors.append(str(err))
    else:
        errors.append('The given sql does not appear to be an INSERT query.')
    result = {'success': not errors}
    if errors:
        result['errors'] = errors
    else:
        result['result'] = 'Data successfully saved to the database.'
    return result


def read_from_database(sql: str, params: tuple=()) -> dict:
    """This function performs a SELECT query on the database, with optional parameters."""
    errors = []
    if sql[:6].upper().find('SELECT') == 0:
        try:
            cursor.execute(sql, params)
            queryresults = [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as err:
            errors.append(str(err))
    else:
        errors.append('The given sql does not appear to be a SELECT query.')
    result = {'success': not errors}
    if errors:
        result['errors'] = errors
    else:
        result['results'] = queryresults
    return result


def update_current_state(data: dict) -> dict:
    """This function writes session id and prism offsets to the currrentstate database table."""
    errors = []
    sql = f"UPDATE currentstate SET {', '.join([f'{key}=?' for key in data])}"
    if not save_to_database(sql, tuple(data.values()))['success']:
            errors.append('An error occurred writing the current state to the database.')
    result = {'status': not errors}
    if errors:
        result['errors'] = errors
    else:
        result['result'] = 'The current state was successfully saved to the database.'
    return result
