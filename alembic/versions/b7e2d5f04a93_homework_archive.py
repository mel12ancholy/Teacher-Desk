"""homework archive: is_archived + archived_at

Revision ID: b7e2d5f04a93
Revises: a1f3c8e92b71
Create Date: 2026-10-24

变更：homeworks 表新增归档字段（is_archived 默认 false / archived_at）。
迁移为手写（autogenerate 会把库中其他项目的 ch_* 表误判为待删除表）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b7e2d5f04a93'
down_revision: Union[str, None] = 'a1f3c8e92b71'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('homeworks') as batch:
        batch.add_column(sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.text('false')))
        batch.add_column(sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('homeworks') as batch:
        batch.drop_column('archived_at')
        batch.drop_column('is_archived')
