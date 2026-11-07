@echo off
cd /d %~dp0
python -m afiliado dia
python -m afiliado sync-metricas
