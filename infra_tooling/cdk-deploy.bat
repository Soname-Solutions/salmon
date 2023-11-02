@findstr /B /V @ %~dpnx0 > %~dpn0.ps1 && powershell -ExecutionPolicy Bypass %~dpn0.ps1 %*
@exit /B %ERRORLEVEL%
if ($args.length -ge 2) {
    $env:AWS_PROFILE, $args = $args
    $env:STAGE,  $args = $args
    npx cdk deploy --profile $env:AWS_PROFILE $args
    exit $lastExitCode
} else {
    [console]::error.writeline("Provide aws profile and stage as first two args.")
    [console]::error.writeline("Additional args are passed through to cdk deploy.")
    exit 1
}
