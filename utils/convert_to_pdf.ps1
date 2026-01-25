$sourceFolder = "$PSScriptRoot\.."
$word = New-Object -ComObject Word.Application
$word.Visible = $false

Get-ChildItem -Path $sourceFolder -Include *.doc, *.docx -Recurse | ForEach-Object {
    $doc = $word.Documents.Open($_.FullName, $false, $true)  # 読み取り専用で開く
    $pdfPath = [System.IO.Path]::ChangeExtension($_.FullName, ".pdf")
    $doc.SaveAs([ref] $pdfPath, [ref] 17)  # 17 = wdFormatPDF
    $doc.Close()
}

$word.Quit()
