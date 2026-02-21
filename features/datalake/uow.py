"""
Unit of Work pattern for DB connection.
See: https://medium.com/technology-hits/unit-of-work-python-domain-driven-design-patterns-f07a675588ee
"""
class UnitOfWork:
    def __init__(self, client):
        self.session = client.start_session()

    def __enter__(self):
        self.session.start_transaction()
        return self.session

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            self.session.abort_transaction()
        else:
            self.session.commit_transaction()
        self.session.end_session()
