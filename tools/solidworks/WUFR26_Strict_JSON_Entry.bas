Attribute VB_Name = "WUFR26_Strict_JSON_Entry"
Option Explicit

' Strict-JSON entrypoint for WUFR26_Metadata_Exporter.
'
' The underlying exporter remains the read-only SOLIDWORKS metadata collector.
' This wrapper only normalizes its derived JSON report after the exporter returns.
' It never saves, rebuilds, activates, or otherwise edits the open SOLIDWORKS model.

Private Const ENTRY_NAME As String = "WUFR26_STRICT_JSON_ENTRY"
Private Const ENTRY_VERSION As String = "1.0.0"

Public Sub main_strict_json()
    On Error GoTo FatalError

    Dim swApp As Object
    Dim swModel As Object
    Dim outputFolder As String
    Dim baseName As String
    Dim startedAt As Date
    Dim outputPath As String
    Dim originalText As String
    Dim normalizedText As String

    Set swApp = Application.SldWorks
    Set swModel = swApp.ActiveDoc

    If swModel Is Nothing Then
        MsgBox "Open the steering assembly or steering part and run the macro again.", _
               vbExclamation, ENTRY_NAME
        Exit Sub
    End If

    outputFolder = DetermineOutputFolder(swModel)
    baseName = SanitizeFileName(RemoveExtension(CStr(swModel.GetTitle)))
    startedAt = Now

    WUFR26_Metadata_Exporter.main

    outputPath = FindNewestOutput(outputFolder, baseName, startedAt)
    If Len(outputPath) = 0 Then
        MsgBox "The exporter returned, but its new metadata JSON report could not be located.", _
               vbExclamation, ENTRY_NAME
        Exit Sub
    End If

    originalText = ReadUtf8File(outputPath)
    normalizedText = NormalizeJsonNumbers(originalText)

    If StrComp(originalText, normalizedText, vbBinaryCompare) <> 0 Then
        WriteUtf8File outputPath, normalizedText
    End If

    MsgBox "Strict JSON normalization complete." & vbCrLf & vbCrLf & outputPath, _
           vbInformation, ENTRY_NAME
    Exit Sub

FatalError:
    MsgBox "Strict JSON normalization failed: " & CStr(Err.Number) & " - " & _
           Err.Description, vbCritical, ENTRY_NAME
End Sub

Private Function FindNewestOutput(ByVal folderPath As String, ByVal baseName As String, _
                                  ByVal startedAt As Date) As String
    On Error GoTo Fail

    Dim fileName As String
    Dim candidatePath As String
    Dim newestPath As String
    Dim newestTime As Date
    Dim candidateTime As Date
    Dim earliestAllowed As Date

    earliestAllowed = DateAdd("s", -10, startedAt)
    fileName = Dir$(folderPath & "\" & baseName & "_*_solidworks_metadata.json")

    Do While Len(fileName) > 0
        candidatePath = folderPath & "\" & fileName
        candidateTime = FileDateTime(candidatePath)
        If candidateTime >= earliestAllowed Then
            If Len(newestPath) = 0 Or candidateTime > newestTime Then
                newestPath = candidatePath
                newestTime = candidateTime
            End If
        End If
        fileName = Dir$()
    Loop

    FindNewestOutput = newestPath
    Exit Function

Fail:
    FindNewestOutput = ""
End Function

Private Function NormalizeJsonNumbers(ByVal value As String) As String
    Dim result As String
    Dim i As Long
    Dim ch As String
    Dim nextCh As String
    Dim afterNext As String
    Dim previousCh As String
    Dim inString As Boolean
    Dim escaped As Boolean

    result = ""
    i = 1

    Do While i <= Len(value)
        ch = Mid$(value, i, 1)

        If inString Then
            result = result & ch
            If escaped Then
                escaped = False
            ElseIf ch = "\" Then
                escaped = True
            ElseIf ch = Chr$(34) Then
                inString = False
            End If
            i = i + 1
        ElseIf ch = Chr$(34) Then
            inString = True
            result = result & ch
            i = i + 1
        Else
            nextCh = ""
            afterNext = ""
            previousCh = ""
            If i < Len(value) Then nextCh = Mid$(value, i + 1, 1)
            If i + 1 < Len(value) Then afterNext = Mid$(value, i + 2, 1)
            If i > 1 Then previousCh = Mid$(value, i - 1, 1)

            If ch = "-" And nextCh = "." And IsDigit(afterNext) And _
               IsJsonNumberBoundary(previousCh) Then
                result = result & "-0."
                i = i + 2
            ElseIf ch = "." And IsDigit(nextCh) And IsJsonNumberBoundary(previousCh) Then
                result = result & "0."
                i = i + 1
            Else
                result = result & ch
                i = i + 1
            End If
        End If
    Loop

    NormalizeJsonNumbers = result
End Function

Private Function IsDigit(ByVal value As String) As Boolean
    IsDigit = (Len(value) = 1 And value >= "0" And value <= "9")
End Function

Private Function IsJsonNumberBoundary(ByVal value As String) As Boolean
    If Len(value) = 0 Then
        IsJsonNumberBoundary = True
        Exit Function
    End If

    Select Case value
        Case " ", vbTab, vbCr, vbLf, "[", "{", ",", ":"
            IsJsonNumberBoundary = True
        Case Else
            IsJsonNumberBoundary = False
    End Select
End Function

Private Function DetermineOutputFolder(ByVal swModel As Object) As String
    Dim modelPath As String

    modelPath = CStr(swModel.GetPathName)
    If Len(modelPath) > 0 Then
        DetermineOutputFolder = FolderFromPath(modelPath)
    Else
        DetermineOutputFolder = CStr(CreateObject("WScript.Shell").SpecialFolders("Desktop"))
    End If
End Function

Private Function ReadUtf8File(ByVal filePath As String) As String
    On Error GoTo Fail

    Dim streamObj As Object
    Set streamObj = CreateObject("ADODB.Stream")
    streamObj.Type = 2
    streamObj.Charset = "utf-8"
    streamObj.Open
    streamObj.LoadFromFile filePath
    ReadUtf8File = streamObj.ReadText
    streamObj.Close
    Exit Function

Fail:
    On Error Resume Next
    If Not streamObj Is Nothing Then streamObj.Close
    On Error GoTo 0
    Err.Raise vbObjectError + 2200, ENTRY_NAME, _
              "Could not read UTF-8 JSON file '" & filePath & "': " & Err.Description
End Function

Private Sub WriteUtf8File(ByVal filePath As String, ByVal content As String)
    On Error GoTo Fail

    Dim streamObj As Object
    Set streamObj = CreateObject("ADODB.Stream")
    streamObj.Type = 2
    streamObj.Charset = "utf-8"
    streamObj.Open
    streamObj.WriteText content
    streamObj.SaveToFile filePath, 2
    streamObj.Close
    Exit Sub

Fail:
    On Error Resume Next
    If Not streamObj Is Nothing Then streamObj.Close
    On Error GoTo 0
    Err.Raise vbObjectError + 2201, ENTRY_NAME, _
              "Could not write strict UTF-8 JSON file '" & filePath & "': " & Err.Description
End Sub

Private Function FolderFromPath(ByVal filePath As String) As String
    Dim position As Long
    position = InStrRev(filePath, "\")
    If position > 0 Then
        FolderFromPath = Left$(filePath, position - 1)
    Else
        FolderFromPath = CurDir$
    End If
End Function

Private Function RemoveExtension(ByVal fileName As String) As String
    Dim position As Long
    position = InStrRev(fileName, ".")
    If position > 1 Then
        RemoveExtension = Left$(fileName, position - 1)
    Else
        RemoveExtension = fileName
    End If
End Function

Private Function SanitizeFileName(ByVal value As String) As String
    Dim badCharacters As Variant
    Dim item As Variant
    Dim result As String

    result = value
    badCharacters = Array("\", "/", ":", "*", "?", Chr$(34), "<", ">", "|")
    For Each item In badCharacters
        result = Replace$(result, CStr(item), "_")
    Next item
    result = Trim$(result)
    If Len(result) = 0 Then result = "solidworks_document"
    SanitizeFileName = result
End Function
