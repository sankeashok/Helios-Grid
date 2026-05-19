@echo off
echo Stopping Helios-Grid Docker Environment...
echo.

docker-compose -f docker-compose.local.yml down

echo.
echo All Helios-Grid services have been stopped.
echo.
pause