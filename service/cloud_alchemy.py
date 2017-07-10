from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Sequence
from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()


def load_sql_session(dbname):
    """Returns sqlalchemy database session"""
    engine = create_engine('sqlite:///{}'.format(dbname), echo=False)
    Session = sessionmaker()
    Session.configure(bind=engine)
    session = Session()
    return session


def create_new_db(dbname):
    engine = create_engine("sqlite:///{}".format(dbname), echo=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker()
    Session.configure(bind=engine)  # once engine is available
    session = Session()
    return session


def create_memory_session():
    """Returns sqlalchemy :memory: database session"""
    engine = create_engine("sqlite:///:memory:", echo=True)
    # the only difference from load_sql_session
    # (other than location) is Base.metadata.create_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker()
    Session.configure(bind=engine)
    session = Session()
    return session


class CloudUser(Base):
    __tablename__ = 'cloud_user'
    user_id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    own_cloud_user = Column(String(50))
    own_cloud_server = Column(String(50))
    sync_files = relationship("CloudFile")
    sync_dirs = relationship("CloudFile")

    def __repr__(self):
        return 'User(own_cloud_user={u}, own_cloud_pass={p}, own_cloud_server={s})'.format(
            u=self.own_cloud_user, p=self.own_cloud_pass, s=self.own_cloud_server)


class CloudFile(Base):
    __tablename__ = 'cloud_file'
    local_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('cloud_user.user_id'))
    date_format = Column(String(50))
    attr_etag = Column(String(50))
    attr_modified = Column(String(50))
    file_type = Column(String(50))
    file_name = Column(String(50))
    file_path = Column(String(254))
    category = Column(String(50))
    rel_path = Column(String(254))
    retrieved = Column(String(50), default="never")

    def __repr__(self):
        return 'CloudFile(date_format={df}, attr_etag={ae}, attr_modified={am}, ' \
               'file_type={ft}, file_name={fn}, file_path={fp}, category={cat})'.format(df=self.date_format,
                                                                                        ae=self.attr_etag,
                                                                                        am=self.attr_modified,
                                                                                        ft=self.file_type,
                                                                                        fn=self.file_name,
                                                                                        fp=self.file_path,
                                                                                        cat=self.category)
