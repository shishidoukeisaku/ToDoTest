from sqlalchemy import ForeignKey, String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.db import Base

from datetime import datetime
from pydantic import BaseModel
from typing import Optional

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db import get_async_session, User
from app.users import fastapi_users

from uuid import UUID


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(length=200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(length=500), nullable=True)
    status: Mapped[bool] = mapped_column(Boolean, default=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ユーザーID（外部キー）
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))

    # リレーション（User → Task）
    user = relationship("User", back_populates="tasks")

# 共通のベーススキーマ
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: bool = False
    due_date: Optional[datetime] = None


# 作成用（user_id は current_user から取得するので受け取らない）
class TaskCreate(TaskBase):
    pass


# 更新用（全部オプションにして部分更新可能にする）
class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[bool] = None
    due_date: Optional[datetime] = None


# 読み取り用（レスポンス）
class TaskRead(TaskBase):
    id: int
    user_id: UUID

    class Config:
        orm_mode = True


tasks_router = APIRouter(prefix="/tasks", tags=["tasks"])

@tasks_router.post("/", response_model=TaskRead)
async def create_task(
    task_in: TaskCreate,
    user: User = Depends(fastapi_users.current_user()),
    session: AsyncSession = Depends(get_async_session),  # ←ここでセッション注入
):
    new_task = Task(**task_in.dict(), user_id=user.id)  # user_id はログインユーザー
    session.add(new_task)  # INSERT 文を準備
    await session.commit()  # 実際に DB に保存
    await session.refresh(new_task)  # DB の値を再取得（id などが反映される）
    return new_task

@tasks_router.get("/", response_model=List[TaskRead])
async def get_tasks(
    user: User = Depends(fastapi_users.current_user()),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(Task).where(Task.user_id == user.id)  # 自分のタスクだけ
    )
    tasks = result.scalars().all()
    return tasks

@tasks_router.put("/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: int,
    task_in: TaskUpdate,
    user: User = Depends(fastapi_users.current_user()),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(Task).where(Task.id == task_id, Task.user_id == user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 更新する値だけ上書き
    for key, value in task_in.dict(exclude_unset=True).items():
        setattr(task, key, value)

    await session.commit()
    await session.refresh(task)  # 更新後の最新状態を取得
    return task

@tasks_router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: int,
    user: User = Depends(fastapi_users.current_user()),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(Task).where(Task.id == task_id, Task.user_id == user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await session.delete(task)  # 削除キューに入れる
    await session.commit()      # 実際に削除
    return None