"""This module handles reading from and writing to the ShootPoints database."""

import sqlite3
import os


dbconn = sqlite3.connect('ShootPoints.db', check_same_thread=False)
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
    if sql[:11].upper().find('INSERT INTO') == 0:
        try:
            cursor.execute(sql, data)
            dbconn.commit()
        except sqlite3.Error as err:
            errors.append(str(err))
    else:
        errors.append('The given sql does not appear to be an INSERT query.')
    outcome = {'success': not errors}
    if errors:
        outcome['errors'] = errors
    else:
        outcome['results'] = 'Data successfully saved to the database.'
    return outcome


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
    outcome = {'success': not errors}
    if errors:
        outcome['errors'] = errors
    else:
        outcome['results'] = queryresults
    return outcome


def update_current_state(data: dict) -> dict:
    """This function writes session id and prism offsets to the currrentstate database table."""
    errors = []
    data = list(data.items())
    sql = f"UPDATE currentstate SET {', '.join([f'{_[0]}=?' for _ in data])}"
    try:
        cursor.execute(sql, tuple(_[1] for _ in data))
        dbconn.commit()
    except sqlite3.Error as err:
        errors.append(str(err))
    outcome = {'success': not errors}
    if errors:
        outcome['errors'] = errors
    else:
        outcome['results'] = 'The current state was successfully saved to the database.'
    return outcome


def _record_setup_error(error: str) -> None:
    sql = 'INSERT INTO setuperrors (error) VALUES (?)'
    try:
        cursor.execute(sql, (error,))
        dbconn.commit()
    except sqlite3.IntegrityError:
        pass


def get_setup_errors() -> list:
    outome = read_from_database('SELECT * FROM setuperrors')
    errors = []
    for each in outome['results']:
        try:
            errors.append(each['error'])
        except:
            pass
    return errors


def _clear_setup_errors() -> None:
    try:
        cursor.execute('DELETE FROM setuperrors')
        dbconn.commit()
    except:
        pass
