# linumeRT · ustawienia PSScriptAnalyzer dla tools/vm/*.ps1 (sesja 025). Model-Author: Claude.
# Wyłączone reguły stylu: skrypty są interaktywne (Write-Host z kolorami), Invoke-VBox to cienkie
# opakowanie wywołań VBoxManage (argumenty pozycyjne), parametry skryptu są używane w funkcjach
# (fałszywe PSReviewUnusedParameter), a funkcje nie obsługują -WhatIf (VBoxManage tego nie ma).
@{
    Severity     = @('Error', 'Warning')
    ExcludeRules = @(
        'PSAvoidUsingWriteHost',
        'PSAvoidUsingPositionalParameters',
        'PSReviewUnusedParameter',
        'PSUseShouldProcessForStateChangingFunctions'
    )
}
