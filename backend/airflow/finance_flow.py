from datetime import datetime

from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.databricks.operators.databricks import (
    DatabricksRunNowOperator,
)


PROJECT_DIR = "/Users/jainil/Documents/development/portfolio-advisor"

BRONZE_LOCAL = f"{PROJECT_DIR}/backend/data/bronze"
SILVER_LOCAL = f"{PROJECT_DIR}/backend/data/silver"

BRONZE_VOLUME = (
    "dbfs:/Volumes/main/default/stock_volume/data/bronze"
)

SILVER_VOLUME = (
    "dbfs:/Volumes/main/default/stock_volume/data/silver"
)


with DAG(
    dag_id="stock_advisor_daily",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
) as dag:

    # 1. Update local data
    update_data = BashOperator(
        task_id="update_data_pipeline",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            f"./venv/bin/python "
            "-m backend.services.data_updates.update_data_pipeline"
        ),
    )

    # 2. Upload bronze data to Databricks Volume
    upload_bronze_data = BashOperator(
        task_id="bronze_upload",
        bash_command=(
            f"databricks fs cp "
            f"{BRONZE_LOCAL} "
            f"{BRONZE_VOLUME} "
            "--recursive"
        ),
    )

    # 3. Run Databricks processing job
    databricks_job_1 = DatabricksRunNowOperator(
        task_id="databricks_job",
        databricks_conn_id="databricks_default",
        job_id=1086762617186571,
    )

    # 4. Download processed silver data
    download_data = BashOperator(
        task_id="download_silver_data",
        bash_command=(
            f"mkdir -p {SILVER_LOCAL} && "
            f"databricks fs cp "
            f"{SILVER_VOLUME} "
            f"{SILVER_LOCAL} "
            "--recursive"
        ),
    )

    # Pipeline order
    (
        update_data
        >> upload_bronze_data
        >> databricks_job_1
        >> download_data
    )