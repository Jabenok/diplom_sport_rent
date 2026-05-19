class Config:
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/rentdb'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'secret-key'
