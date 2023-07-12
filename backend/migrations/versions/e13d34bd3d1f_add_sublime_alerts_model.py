"""Add sublime alerts model.

Revision ID: e13d34bd3d1f
Revises: 0381c0088cbe
Create Date: 2023-07-12 11:47:15.118862

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e13d34bd3d1f"
down_revision = "0381c0088cbe"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("case")
    op.drop_table("graylog_metrics_allocation")
    op.drop_table("artifact")
    op.drop_table("wazuh_indexer_allocation")
    with op.batch_alter_table("sublime_alerts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("timestamp", sa.DateTime(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("sublime_alerts", schema=None) as batch_op:
        batch_op.drop_column("timestamp")

    op.create_table(
        "wazuh_indexer_allocation",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("node", sa.VARCHAR(length=100), nullable=True),
        sa.Column("disk_used", sa.FLOAT(), nullable=True),
        sa.Column("disk_available", sa.FLOAT(), nullable=True),
        sa.Column("disk_total", sa.FLOAT(), nullable=True),
        sa.Column("disk_percent", sa.FLOAT(), nullable=True),
        sa.Column("timestamp", sa.DATETIME(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "artifact",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("artifact_name", sa.VARCHAR(length=100), nullable=True),
        sa.Column("artifact_results", sa.TEXT(), nullable=True),
        sa.Column("hostname", sa.VARCHAR(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "graylog_metrics_allocation",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("input_usage", sa.FLOAT(), nullable=True),
        sa.Column("output_usage", sa.FLOAT(), nullable=True),
        sa.Column("processor_usage", sa.FLOAT(), nullable=True),
        sa.Column("input_1_sec_rate", sa.FLOAT(), nullable=True),
        sa.Column("output_1_sec_rate", sa.FLOAT(), nullable=True),
        sa.Column("total_input", sa.FLOAT(), nullable=True),
        sa.Column("total_output", sa.FLOAT(), nullable=True),
        sa.Column("timestamp", sa.DATETIME(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "case",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("case_id", sa.INTEGER(), nullable=True),
        sa.Column("case_name", sa.VARCHAR(length=100), nullable=True),
        sa.Column("agents", sa.VARCHAR(length=1000), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###