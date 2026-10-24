"""Service base from which all CRUD services inherit."""

import logging

lgr = logging.getLogger(__name__)


class ServiceBase(object):
    """CRUD wrapper around a model manager."""

    manager = None

    def __init__(self, lock_for_update=False, *args, **annotations):
        """Initializes the service and optionally locks or annotates the manager.
		@param lock_for_update: Whether retrieved rows stay locked for the rest of the transaction.
		@type lock_for_update: bool
		@param args: Ordered (name, expression) annotations.
		@type args: tuple
		@param annotations: Annotations applied ahead of any filters.
		@type annotations: dict
		@return: None
		@rtype: None"""
        super(ServiceBase, self).__init__()
        if lock_for_update and self.manager is not None:
            self.manager = self.manager.select_for_update()
        for arg in args:
            if isinstance(arg, tuple) and len(arg) == 2:
                self.manager = self.manager.annotate(**{str(arg[0]): arg[1]})
        if annotations:
            self.manager = self.manager.annotate(**annotations)

    def get(self, *args, **kwargs):
        """Gets a single record from the manager.
		@param args: Positional arguments passed to the manager get method.
		@type args: tuple
		@param kwargs: Keyword arguments passed to the manager get method.
		@type kwargs: dict
		@return: The matching record, or None when it does not exist.
		@rtype: object | None"""
        try:
            if self.manager is not None:
                return self.manager.get(*args, **kwargs)
        except self.manager.model.DoesNotExist:
            return None
        except Exception as e:
            lgr.exception('%sService get exception: %s', self.manager.model.__name__, e)
        return None

    def filter(self, *args, **kwargs):
        """Returns a queryset from the manager.
		@param args: Positional arguments passed to the manager filter method.
		@type args: tuple
		@param kwargs: Keyword arguments passed to the manager filter method.
		@type kwargs: dict
		@return: The queryset, or None when the manager is missing or the query fails.
		@rtype: QuerySet | None"""
        try:
            if self.manager is not None:
                return self.manager.filter(*args, **kwargs)
        except Exception as e:
            lgr.exception('%sService filter exception: %s', self.manager.model.__name__, e)
        return None

    def create(self, **kwargs):
        """Creates one record.
		@param kwargs: Field values for the new record.
		@type kwargs: dict
		@return: The created record, or None on error.
		@rtype: object | None"""
        try:
            if self.manager is not None:
                return self.manager.create(**kwargs)
        except Exception as e:
            lgr.exception('%s Service create exception: %s', self.manager.model.__name__, e)
        return None

    def update(self, pk, **kwargs):
        """Updates the record with the given primary key.
		@param pk: Primary key of the record to update.
		@type pk: object
		@param kwargs: Field values to set on the record.
		@type kwargs: dict
		@return: The updated record, or None on error.
		@rtype: object | None"""
        try:
            record = self.get(id=pk)
            if record is not None:
                for key, value in kwargs.items():
                    setattr(record, key, value)
                record.save()
                record.refresh_from_db()
                return record
        except Exception as e:
            lgr.exception('%sService update exception: %s', self.manager.model.__name__, e)
        return None

    def re_update(self, pk, **kwargs):
        """Updates the record with the given primary key.
		@param pk: Primary key of the record to update.
		@type pk: object
		@param kwargs: Field values to set on the record.
		@type kwargs: dict
		@return: The updated record, or None on error.
		@rtype: object | None"""
        return self.update(pk, **kwargs)
