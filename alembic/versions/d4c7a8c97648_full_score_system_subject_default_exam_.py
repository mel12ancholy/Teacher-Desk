"""full score system: subject default + exam type + exam instance

Revision ID: d4c7a8c97648
Revises: 4f0f45de5d48
Create Date: 2026-10-24 11:30:04.956288

注意：autogenerate 曾误将库中其他项目的表（ch_* 系列）渲染为 drop_table，
本文件已手工修正为仅包含本项目的三处结构变更：
1. subjects.full_score 列（默认 100）
2. exam_type_full_scores 表（科目 × 考试类型默认满分）
3. exam_full_scores 表（场次实例满分）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd4c7a8c97648'
down_revision: Union[str, None] = '4f0f45de5d48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('exam_full_scores',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('class_id', sa.Integer(), nullable=False),
    sa.Column('subject_id', sa.Integer(), nullable=False),
    sa.Column('exam_type', sa.String(), nullable=False),
    sa.Column('exam_date', sa.Date(), nullable=False),
    sa.Column('full_score', sa.Float(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['class_id'], ['classes.id'], ),
    sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('class_id', 'subject_id', 'exam_type', 'exam_date', name='uq_exam_full_score')
    )
    op.create_index(op.f('ix_exam_full_scores_id'), 'exam_full_scores', ['id'], unique=False)
    op.create_table('exam_type_full_scores',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('subject_id', sa.Integer(), nullable=False),
    sa.Column('exam_type', sa.String(), nullable=False),
    sa.Column('full_score', sa.Float(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('subject_id', 'exam_type', name='uq_exam_type_full_score')
    )
    op.create_index(op.f('ix_exam_type_full_scores_id'), 'exam_type_full_scores', ['id'], unique=False)
    # 既有科目默认满分 100（server_default 保证 NOT NULL 直接生效）
    op.add_column('subjects', sa.Column('full_score', sa.Float(), nullable=False, server_default='100'))


def downgrade() -> None:
    op.drop_column('subjects', 'full_score')
    op.drop_index(op.f('ix_exam_type_full_scores_id'), table_name='exam_type_full_scores')
    op.drop_table('exam_type_full_scores')
    op.drop_index(op.f('ix_exam_full_scores_id'), table_name='exam_full_scores')
    op.drop_table('exam_full_scores')
