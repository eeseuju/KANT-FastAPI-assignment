from sqlalchemy.orm import DeclarativeBase


# 모든 모델이 상속받는 부모 클래스
class Base(DeclarativeBase):
    pass