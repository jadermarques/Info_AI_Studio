.PHONY: gui cli test backup

ENV?=.env

gui:
streamlit run src/app/interfaces/web/app.py

cli:
python -m app.interfaces.cli.main --help

test:
pytest

backup:
python -m app.interfaces.cli.main db-backup
