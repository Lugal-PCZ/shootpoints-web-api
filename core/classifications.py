"""This module contains functions for reading, creating, and removing classes and subclasses of archaeological survey data."""

from . import _database


def get_classes_and_subclasses() -> dict:
    """This function returns all the classes and subclasses in the database."""
    outcome = {'errors': [], 'results': []}
    classes = _database.read_from_database('SELECT * FROM classes ORDER BY name')
    if classes['success']:
        for each_class in classes['results']:
            subclasses = _database.read_from_database('SELECT id, name FROM subclasses WHERE classes_id = ? ORDER BY name', (each_class['id'],))
            if subclasses['success']:
                each_class['subclasses'] = subclasses['results']
                outcome['results'].append(each_class)
            else:
                outcome['errors'] = subclasses['errors']
    else:
        outcome['errors'] = classes['errors']
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if val or key == 'success'}


def create_new_class(name: str, description: str=None) -> dict:
    """This function saves a new class to the database."""
    outcome = {'errors': [], 'results': ''}
    sql = 'INSERT INTO classes (name) VALUES(?)'
    newclass = _database.save_to_database(sql, (name.strip().title(), description.strip()))
    if newclass['success']:
        outcome['result'] = f'Class “{name}” successfully saved to the database.'
    else:
        outcome['errors'] = newclass['errors']
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if val or key == 'success'}


def create_new_subclass(classes_id: int, name: str, description: str=None) -> dict:
    """This function saves a new subclass to the database."""
    outcome = {'errors': [], 'results': ''}
    sql = 'INSERT INTO subclasses (classes_id, name) VALUES(?, ?)'
    newclass = _database.save_to_database(sql, (classes_id, name.strip().title(), description.strip()))
    if newclass['success']:
        outcome['result'] = f'Sublass “{name}” successfully saved to the database.'
    else:
        outcome['errors'] = newclass['errors']
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if val or key == 'success'}


def delete_class(id: int) -> dict:
    """This function deletes the indicated class from the database."""
    outcome = {'errors': [], 'results': ''}
    exists = _database.read_from_database('SELECT name FROM classes WHERE id = ?', (id,))
    if exists['success']:
        try:
            name = exists['results'][0]['name']
            sql = 'DELETE FROM classes WHERE id = ?'
            deleted = _database.delete_from_database(sql, (id,))
            if deleted['success']:
                outcome['result'] = f'Class “{name}” successfully deleted from the database.'
            else:
                outcome['errors'] = deleted['errors']
        except IndexError:
            outcome['errors'].append(f'Class id {id} does not exist.')
        if outcome['errors'][0] == 'FOREIGN KEY constraint failed':
            outcome['errors'][0] = f'Class “{name}” could not be deleted because it is a foreign key for one or more subclasses.'
    else:
        outcome['errors'] = exists['errors']
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if val or key == 'success'}


def delete_subclass(id: int) -> dict:
    """This function deletes the indicated subclass from the database."""
    outcome = {'errors': [], 'results': ''}
    exists = _database.read_from_database('SELECT name FROM subclasses WHERE id = ?', (id,))
    if exists['success']:
        try:
            name = exists['results'][0]['name']
            sql = 'DELETE FROM subclasses WHERE id = ?'
            deleted = _database.delete_from_database(sql, (id,))
            if deleted['success']:
                outcome['result'] = f'Subclass “{name}” successfully deleted from the database.'
            else:
                outcome['errors'] = deleted['errors']
        except IndexError:
            outcome['errors'].append(f'Subclass id {id} does not exist.')
        if outcome['errors'][0] == 'FOREIGN KEY constraint failed':
            outcome['errors'][0] = f'Subclass “{name}” could not be deleted because it is a foreign key for one or more groupings.'
    else:
        outcome['errors'] = exists['errors']
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if val or key == 'success'}
