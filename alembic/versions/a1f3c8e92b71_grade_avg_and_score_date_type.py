"""grade subject averages + scores.exam_date to date-only

Revision ID: a1f3c8e92b71
Revises: d4c7a8c97648
Create Date: 2026-10-24

变更内容：
1. 新表 grade_subject_averages（人工录入的年级单科平均分）
2. scores.exam_date 由 timestamptz 改为 Date（现值均为 00:00:00，USING ::date 无损转换；
   考试聚合键本就只取日期部分，转换后既有考试 key 不变）

注意：迁移为手写（autogenerate 会把库中其他项目的 ch_* 表误判为待删除表）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1f3c8e92b71'
down_revision: Union[str, None] = 'd4c7a8c97648'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('grade_subject_averages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('semester', sa.String(), nullable=False),
    sa.Column('exam_type', sa.String(), nullable=False),
    sa.Column('exam_date', sa.Date(), nullable=False),
    sa.Column('subject_id', sa.Integer(), nullable=False),
    sa.Column('avg_score', sa.Float(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('semester', 'exam_type', 'exam_date', 'subject_id', name='uq_grade_avg')
    )
    op.create_index(op.f('ix_grade_subject_averages_id'), 'grade_subject_averages', ['id'], unique=False)

    # scores.exam_date → Date（batch 模式在 SQLite 重建表，在 PostgreSQL 直接 ALTER ... USING）
    with op.batch_alter_table('scores') as batch:
        batch.alter_column(
            'exam_date',
            existing_type=sa.DateTime(timezone=True),
            type_=sa.Date(),
            existing_nullable=True,
            postgresql_using='exam_date::date'
        )


def downgrade() -> None:
    with op.batch_alter_table('scores') as batch:
        batch.alter_column(
            'exam_date',
            existing_type=sa.Date(),
            type_=sa.DateTime(timezone=True),
            existing_nullable=True
        )
    op.drop_index(op.f('ix_grade_subject_averages_id'), table_name='grade_subject_averages')
    op.drop_table('grade_subject_averages')
