Attribute VB_Name = "SW_Metadata_Exporter"
Option Explicit

' SOLIDWORKS Metadata Exporter v1.0.1
' Read-only: does not save, rebuild, switch configurations, activate studies,
' resolve components, or alter suppression state.

Private Const MACRO_VERSION As String = "1.0.1"
Private Const SW_DOC_PART As Long = 1
Private Const SW_DOC_ASSEMBLY As Long = 2
Private Const SW_DOC_DRAWING As Long = 3

Private Const SW_EXTREF_BROKEN As Long = 0
Private Const SW_EXTREF_LOCKED As Long = 1
Private Const SW_EXTREF_IN_CONTEXT As Long = 3
Private Const SW_EXTREF_OUT_OF_CONTEXT As Long = 4
Private Const SW_EXTREF_DANGLING As Long = 5

Public Sub main()
    Dim swApp As Object
    Dim swModel As Object
    Dim outputDir As String
    Dim warnings As Collection
    Dim counts As Object

    On Error GoTo FatalError

    Set swApp = Application.SldWorks
    Set swModel = swApp.ActiveDoc

    If swModel Is Nothing Then
        MsgBox "Open the SOLIDWORKS part or assembly to inspect, then run the macro again.", _
               vbExclamation, "SOLIDWORKS Metadata Exporter"
        Exit Sub
    End If

    outputDir = PromptForOutputDirectory(swModel)
    If Len(outputDir) = 0 Then Exit Sub
    EnsureFolderTree outputDir

    Set warnings = New Collection
    Set counts = CreateObject("Scripting.Dictionary")

    counts("configurations") = ExportConfigurations(swModel, JoinPath(outputDir, "configurations.csv"), warnings)
    counts("custom_properties") = ExportCustomProperties(swModel, JoinPath(outputDir, "custom_properties.csv"), warnings)
    counts("equations") = ExportEquations(swModel, JoinPath(outputDir, "equations.csv"), warnings)
    counts("external_references") = ExportExternalReferences(swModel, JoinPath(outputDir, "external_references.csv"), warnings)
    counts("components") = ExportComponents(swModel, JoinPath(outputDir, "components.csv"), warnings)
    counts("features") = ExportFeatures(swModel, JoinPath(outputDir, "features.csv"), warnings)
    counts("dimensions") = ExportDimensions(swModel, JoinPath(outputDir, "dimensions.csv"), warnings)
    counts("motion_studies") = ExportMotionStudies(swModel, JoinPath(outputDir, "motion_studies.csv"), warnings)

    ExportManifestJson swApp, swModel, outputDir, counts, warnings
    ExportReadme outputDir

    MsgBox "Metadata package written to:" & vbCrLf & outputDir & vbCrLf & vbCrLf & _
           "Start with solidworks_metadata.json and README.txt.", _
           vbInformation, "SOLIDWORKS Metadata Export Complete"
    Exit Sub

FatalError:
    MsgBox "Metadata export failed." & vbCrLf & _
           "Error " & CStr(Err.Number) & ": " & Err.Description, _
           vbCritical, "SOLIDWORKS Metadata Exporter"
End Sub

Private Function PathSep() As String
    PathSep = Chr$(92)
End Function

Private Function PromptForOutputDirectory(ByVal swModel As Object) As String
    Dim sourcePath As String
    Dim baseDir As String
    Dim modelStem As String
    Dim defaultDir As String
    Dim shellObj As Object

    sourcePath = SafeModelPath(swModel)
    If Len(sourcePath) > 0 Then
        baseDir = Left$(sourcePath, InStrRev(sourcePath, PathSep()) - 1)
        modelStem = FileStem(sourcePath)
    Else
        On Error Resume Next
        Set shellObj = CreateObject("WScript.Shell")
        baseDir = shellObj.SpecialFolders("Desktop")
        On Error GoTo 0
        If Len(baseDir) = 0 Then baseDir = Environ$("USERPROFILE") & PathSep() & "Desktop"
        modelStem = "UNSAVED_MODEL"
    End If

    defaultDir = JoinPath(baseDir, "SW_METADATA_" & SafeFileName(modelStem) & "_" & _
                          Format$(Now, "yyyymmdd_hhnnss"))

    PromptForOutputDirectory = InputBox( _
        "Enter the output folder for the metadata package." & vbCrLf & _
        "The source model will not be saved or modified.", _
        "SOLIDWORKS Metadata Exporter", defaultDir)
End Function

Private Sub EnsureFolderTree(ByVal folderPath As String)
    Dim fso As Object
    Dim parentPath As String

    Set fso = CreateObject("Scripting.FileSystemObject")
    If fso.FolderExists(folderPath) Then Exit Sub

    parentPath = fso.GetParentFolderName(folderPath)
    If Len(parentPath) > 0 And Not fso.FolderExists(parentPath) Then
        EnsureFolderTree parentPath
    End If
    fso.CreateFolder folderPath
End Sub

Private Function JoinPath(ByVal leftPath As String, ByVal rightPath As String) As String
    If Right$(leftPath, 1) = PathSep() Then
        JoinPath = leftPath & rightPath
    Else
        JoinPath = leftPath & PathSep() & rightPath
    End If
End Function

Private Function FileStem(ByVal filePath As String) As String
    Dim fileName As String
    Dim dotPos As Long

    fileName = Mid$(filePath, InStrRev(filePath, PathSep()) + 1)
    dotPos = InStrRev(fileName, ".")
    If dotPos > 1 Then
        FileStem = Left$(fileName, dotPos - 1)
    Else
        FileStem = fileName
    End If
End Function

Private Function SafeFileName(ByVal value As String) As String
    Dim badChars As Variant
    Dim item As Variant

    badChars = Array(PathSep(), "/", ":", "*", "?", Chr$(34), "<", ">", "|")
    SafeFileName = value
    For Each item In badChars
        SafeFileName = Replace$(SafeFileName, CStr(item), "_")
    Next item
    If Len(SafeFileName) = 0 Then SafeFileName = "MODEL"
End Function

Private Sub WriteTextFile(ByVal filePath As String, ByVal text As String)
    Dim stream As Object
    Dim fileNo As Integer

    On Error GoTo PlainTextFallback
    Set stream = CreateObject("ADODB.Stream")
    stream.Type = 2
    stream.Charset = "utf-8"
    stream.Open
    stream.WriteText text
    stream.SaveToFile filePath, 2
    stream.Close
    Exit Sub

PlainTextFallback:
    On Error Resume Next
    If Not stream Is Nothing Then stream.Close
    On Error GoTo 0
    fileNo = FreeFile
    Open filePath For Output As #fileNo
    Print #fileNo, text;
    Close #fileNo
End Sub

Private Sub AppendLine(ByRef buffer As String, ByVal lineText As String)
    buffer = buffer & lineText & vbCrLf
End Sub

Private Function ExportConfigurations(ByVal swModel As Object, ByVal outputPath As String, _
                                      ByVal warnings As Collection) As Long
    Dim csv As String
    Dim names As Variant
    Dim cfg As Object
    Dim parentCfg As Object
    Dim i As Long
    Dim activeName As String
    Dim cfgName As String
    Dim altName As String
    Dim description As String
    Dim parentName As String
    Dim displayStates As String

    AppendLine csv, "configuration_name,is_active,is_derived,parent_configuration,alternate_name,description,display_states"
    activeName = SafeActiveConfigurationName(swModel)

    On Error GoTo ExportError
    names = swModel.GetConfigurationNames
    If Not IsArray(names) Then
        WriteTextFile outputPath, csv
        Exit Function
    End If

    For i = LBound(names) To UBound(names)
        cfgName = CStr(names(i))
        Set cfg = Nothing
        Set parentCfg = Nothing
        altName = ""
        description = ""
        parentName = ""
        displayStates = ""

        Set cfg = swModel.GetConfigurationByName(cfgName)
        If Not cfg Is Nothing Then
            On Error Resume Next
            altName = CStr(cfg.AlternateName)
            description = CStr(cfg.Description)
            displayStates = JoinVariant(cfg.GetDisplayStates, "|")
            Set parentCfg = cfg.GetParent
            If Not parentCfg Is Nothing Then parentName = CStr(parentCfg.Name)
            On Error GoTo ExportError
        End If

        AppendLine csv, CsvEscape(cfgName) & "," & _
                        CsvEscape(BoolText(StrComp(cfgName, activeName, vbTextCompare) = 0)) & "," & _
                        CsvEscape(BoolText(Len(parentName) > 0)) & "," & _
                        CsvEscape(parentName) & "," & CsvEscape(altName) & "," & _
                        CsvEscape(description) & "," & CsvEscape(displayStates)
        ExportConfigurations = ExportConfigurations + 1
    Next i

    WriteTextFile outputPath, csv
    Exit Function

ExportError:
    warnings.Add "Configuration export stopped early: " & Err.Description
    WriteTextFile outputPath, csv
End Function

Private Function ExportCustomProperties(ByVal swModel As Object, ByVal outputPath As String, _
                                        ByVal warnings As Collection) As Long
    Dim csv As String
    Dim names As Variant
    Dim i As Long

    AppendLine csv, "scope,property_name,type_code,expression,resolved_value,is_linked"
    ExportCustomProperties = ExportPropertyScope(swModel, "", "document", csv, warnings)

    On Error GoTo ExportError
    names = swModel.GetConfigurationNames
    If IsArray(names) Then
        For i = LBound(names) To UBound(names)
            ExportCustomProperties = ExportCustomProperties + _
                ExportPropertyScope(swModel, CStr(names(i)), "configuration:" & CStr(names(i)), csv, warnings)
        Next i
    End If

    WriteTextFile outputPath, csv
    Exit Function

ExportError:
    warnings.Add "Custom-property export stopped early: " & Err.Description
    WriteTextFile outputPath, csv
End Function

Private Function ExportPropertyScope(ByVal swModel As Object, ByVal managerScope As String, _
                                     ByVal exportedScope As String, ByRef csv As String, _
                                     ByVal warnings As Collection) As Long
    Dim mgr As Object
    Dim names As Variant
    Dim types As Variant
    Dim values As Variant
    Dim resolved As Variant
    Dim links As Variant
    Dim count As Long
    Dim i As Long

    On Error GoTo ScopeError
    Set mgr = swModel.Extension.CustomPropertyManager(managerScope)
    count = mgr.GetAll3(names, types, values, resolved, links)

    For i = 0 To count - 1
        AppendLine csv, CsvEscape(exportedScope) & "," & _
                        CsvEscape(CStr(SafeVariantAt(names, i))) & "," & _
                        CsvEscape(CStr(SafeVariantAt(types, i))) & "," & _
                        CsvEscape(CStr(SafeVariantAt(values, i))) & "," & _
                        CsvEscape(CStr(SafeVariantAt(resolved, i))) & "," & _
                        CsvEscape(BoolText(VariantToBoolean(SafeVariantAt(links, i))))
        ExportPropertyScope = ExportPropertyScope + 1
    Next i
    Exit Function

ScopeError:
    warnings.Add "Could not read custom properties for '" & exportedScope & "': " & Err.Description
End Function

Private Function ExportEquations(ByVal swModel As Object, ByVal outputPath As String, _
                                 ByVal warnings As Collection) As Long
    Dim csv As String
    Dim mgr As Object
    Dim count As Long
    Dim i As Long
    Dim eqText As String
    Dim disabledText As String
    Dim globalText As String
    Dim valueText As String
    Dim linkedText As String
    Dim linkedFile As String

    AppendLine csv, "index,equation,is_disabled,is_global_variable,current_value,manager_linked_to_file,manager_file_path,keyword_hits"

    On Error GoTo ExportError
    Set mgr = swModel.GetEquationMgr
    If mgr Is Nothing Then
        WriteTextFile outputPath, csv
        Exit Function
    End If

    On Error Resume Next
    linkedText = BoolText(CBool(mgr.LinkToFile))
    linkedFile = CStr(mgr.FilePath)
    On Error GoTo ExportError

    count = mgr.GetCount
    For i = 0 To count - 1
        eqText = ""
        disabledText = ""
        globalText = ""
        valueText = ""
        On Error Resume Next
        eqText = CStr(mgr.Equation(i))
        disabledText = BoolText(CBool(mgr.Disabled(i)))
        globalText = BoolText(CBool(mgr.GlobalVariable(i)))
        valueText = CStr(mgr.Value(i))
        On Error GoTo ExportError

        AppendLine csv, CsvEscape(CStr(i)) & "," & CsvEscape(eqText) & "," & _
                        CsvEscape(disabledText) & "," & CsvEscape(globalText) & "," & _
                        CsvEscape(valueText) & "," & CsvEscape(linkedText) & "," & _
                        CsvEscape(linkedFile) & "," & CsvEscape(MetadataHits(eqText))
        ExportEquations = ExportEquations + 1
    Next i

    WriteTextFile outputPath, csv
    Exit Function

ExportError:
    warnings.Add "Equation export stopped early: " & Err.Description
    WriteTextFile outputPath, csv
End Function

Private Function ExportExternalReferences(ByVal swModel As Object, ByVal outputPath As String, _
                                          ByVal warnings As Collection) As Long
    Dim csv As String
    Dim modelPaths As Variant
    Dim componentPaths As Variant
    Dim features As Variant
    Dim dataTypes As Variant
    Dim statuses As Variant
    Dim refEntities As Variant
    Dim featureComponents As Variant
    Dim configOptions As Variant
    Dim configNames As Variant
    Dim rowCount As Long
    Dim i As Long
    Dim statusValue As Variant

    AppendLine csv, "model_path,component_path,feature,data_type,status_code,status_name,reference_entity,feature_component,configuration_option,configuration_names"

    On Error GoTo ExportError
    swModel.Extension.ListExternalFileReferences2 modelPaths, componentPaths, features, dataTypes, _
        statuses, refEntities, featureComponents, configOptions, configNames

    rowCount = MaximumVariantArrayCount(Array(modelPaths, componentPaths, features, dataTypes, _
        statuses, refEntities, featureComponents, configOptions, configNames))

    For i = 0 To rowCount - 1
        statusValue = SafeVariantAt(statuses, i)
        AppendLine csv, CsvEscape(CStr(SafeVariantAt(modelPaths, i))) & "," & _
                        CsvEscape(CStr(SafeVariantAt(componentPaths, i))) & "," & _
                        CsvEscape(CStr(SafeVariantAt(features, i))) & "," & _
                        CsvEscape(CStr(SafeVariantAt(dataTypes, i))) & "," & _
                        CsvEscape(CStr(statusValue)) & "," & _
                        CsvEscape(ExternalReferenceStatusName(statusValue)) & "," & _
                        CsvEscape(CStr(SafeVariantAt(refEntities, i))) & "," & _
                        CsvEscape(CStr(SafeVariantAt(featureComponents, i))) & "," & _
                        CsvEscape(CStr(SafeVariantAt(configOptions, i))) & "," & _
                        CsvEscape(CStr(SafeVariantAt(configNames, i)))
        ExportExternalReferences = ExportExternalReferences + 1
    Next i

    WriteTextFile outputPath, csv
    Exit Function

ExportError:
    warnings.Add "External-reference API was incomplete: " & Err.Description & _
                 ". Also capture File > Find References and the External References dialog."
    WriteTextFile outputPath, csv
End Function

Private Function ExportComponents(ByVal swModel As Object, ByVal outputPath As String, _
                                  ByVal warnings As Collection) As Long
    Dim csv As String
    Dim swAssembly As Object
    Dim components As Variant
    Dim comp As Object
    Dim parentComp As Object
    Dim i As Long
    Dim suppressionCode As Long
    Dim parentName As String
    Dim refDisplayState As String

    AppendLine csv, "component_name,parent_component,path,referenced_configuration,referenced_display_state,suppression_code,suppression_name,is_loaded,is_suppressed,visibility_code,is_fixed,is_virtual,is_envelope,is_mirrored,is_pattern_instance,solving_option,keyword_hits"

    If swModel.GetType <> SW_DOC_ASSEMBLY Then
        WriteTextFile outputPath, csv
        Exit Function
    End If

    On Error GoTo ExportError
    Set swAssembly = swModel
    components = swAssembly.GetComponents(False)
    If Not IsArray(components) Then
        WriteTextFile outputPath, csv
        Exit Function
    End If

    For i = LBound(components) To UBound(components)
        Set comp = components(i)
        Set parentComp = Nothing
        parentName = ""
        refDisplayState = ""
        suppressionCode = -999

        On Error Resume Next
        Set parentComp = comp.GetParent
        If Not parentComp Is Nothing Then parentName = CStr(parentComp.Name2)
        suppressionCode = CLng(comp.GetSuppression2)
        refDisplayState = CStr(comp.ReferencedDisplayState2)
        On Error GoTo ExportError

        AppendLine csv, CsvEscape(CStr(comp.Name2)) & "," & CsvEscape(parentName) & "," & _
                        CsvEscape(CStr(comp.GetPathName)) & "," & _
                        CsvEscape(CStr(comp.ReferencedConfiguration)) & "," & _
                        CsvEscape(refDisplayState) & "," & CsvEscape(CStr(suppressionCode)) & "," & _
                        CsvEscape(ComponentSuppressionName(suppressionCode)) & "," & _
                        CsvEscape(SafeBoolMethod(comp, "IsLoaded")) & "," & _
                        CsvEscape(SafeBoolMethod(comp, "IsSuppressed")) & "," & _
                        CsvEscape(SafeProperty(comp, "Visible")) & "," & _
                        CsvEscape(SafeBoolMethod(comp, "IsFixed")) & "," & _
                        CsvEscape(SafeProperty(comp, "IsVirtual")) & "," & _
                        CsvEscape(SafeBoolMethod(comp, "IsEnvelope")) & "," & _
                        CsvEscape(SafeBoolMethod(comp, "IsMirrored")) & "," & _
                        CsvEscape(SafeBoolMethod(comp, "IsPatternInstance")) & "," & _
                        CsvEscape(SafeProperty(comp, "Solving")) & "," & _
                        CsvEscape(MetadataHits(CStr(comp.Name2) & " " & CStr(comp.GetPathName)))
        ExportComponents = ExportComponents + 1
    Next i

    warnings.Add "components.csv describes the active assembly configuration only. The macro does not activate other configurations or resolve lightweight components."
    WriteTextFile outputPath, csv
    Exit Function

ExportError:
    warnings.Add "Component export stopped early: " & Err.Description
    WriteTextFile outputPath, csv
End Function

Private Function ExportFeatures(ByVal swModel As Object, ByVal outputPath As String, _
                                ByVal warnings As Collection) As Long
    Dim csv As String
    Dim feat As Object
    Dim featName As String
    Dim typeName As String

    AppendLine csv, "feature_name,type_name,is_suppressed_current,visibility_code,update_stamp,keyword_hits"

    On Error GoTo ExportError
    Set feat = swModel.FirstFeature
    Do While Not feat Is Nothing
        featName = SafeProperty(feat, "Name")
        typeName = SafeMethod(feat, "GetTypeName2")
        AppendLine csv, CsvEscape(featName) & "," & CsvEscape(typeName) & "," & _
                        CsvEscape(SafeBoolMethod(feat, "IsSuppressed")) & "," & _
                        CsvEscape(SafeProperty(feat, "Visible")) & "," & _
                        CsvEscape(SafeMethod(feat, "GetUpdateStamp")) & "," & _
                        CsvEscape(MetadataHits(featName & " " & typeName))
        ExportFeatures = ExportFeatures + 1
        Set feat = feat.GetNextFeature
    Loop

    WriteTextFile outputPath, csv
    Exit Function

ExportError:
    warnings.Add "Feature export stopped early: " & Err.Description
    WriteTextFile outputPath, csv
End Function

Private Function ExportDimensions(ByVal swModel As Object, ByVal outputPath As String, _
                                  ByVal warnings As Collection) As Long
    Dim csv As String
    Dim feat As Object
    Dim dispDim As Object
    Dim dimObj As Object
    Dim seen As Object
    Dim fullName As String
    Dim uniqueKey As String
    Dim featName As String

    AppendLine csv, "feature_name,dimension_name,full_name,selection_name,system_value_current,display_type,linked_text,keyword_hits"
    Set seen = CreateObject("Scripting.Dictionary")

    On Error GoTo ExportError
    Set feat = swModel.FirstFeature
    Do While Not feat Is Nothing
        featName = SafeProperty(feat, "Name")
        Set dispDim = Nothing
        On Error Resume Next
        Set dispDim = feat.GetFirstDisplayDimension
        On Error GoTo ExportError

        Do While Not dispDim Is Nothing
            Set dimObj = Nothing
            fullName = ""
            On Error Resume Next
            Set dimObj = dispDim.GetDimension2(0)
            If Not dimObj Is Nothing Then fullName = CStr(dimObj.FullName)
            On Error GoTo ExportError

            uniqueKey = fullName
            If Len(uniqueKey) = 0 Then uniqueKey = featName & "|" & SafeProperty(dimObj, "Name")

            If Not seen.Exists(uniqueKey) Then
                seen.Add uniqueKey, True
                AppendLine csv, CsvEscape(featName) & "," & _
                                CsvEscape(SafeProperty(dimObj, "Name")) & "," & _
                                CsvEscape(fullName) & "," & _
                                CsvEscape(SafeMethod(dimObj, "GetNameForSelection")) & "," & _
                                CsvEscape(SafeProperty(dimObj, "SystemValue")) & "," & _
                                CsvEscape(SafeProperty(dispDim, "Type2")) & "," & _
                                CsvEscape(SafeMethod(dispDim, "GetLinkedText")) & "," & _
                                CsvEscape(MetadataHits(featName & " " & fullName & " " & _
                                                       SafeMethod(dispDim, "GetLinkedText")))
                ExportDimensions = ExportDimensions + 1
            End If

            Set dispDim = feat.GetNextDisplayDimension(dispDim)
        Loop
        Set feat = feat.GetNextFeature
    Loop

    If ExportDimensions = 0 Then
        warnings.Add "No feature display dimensions were returned. Dimension enumeration is best-effort and can depend on document state."
    End If
    WriteTextFile outputPath, csv
    Exit Function

ExportError:
    warnings.Add "Dimension export stopped early: " & Err.Description
    WriteTextFile outputPath, csv
End Function

Private Function ExportMotionStudies(ByVal swModel As Object, ByVal outputPath As String, _
                                     ByVal warnings As Collection) As Long
    Dim csv As String
    Dim mgr As Object
    Dim study As Object
    Dim names As Variant
    Dim i As Long
    Dim studyType As Long
    Dim studyName As String

    AppendLine csv, "study_name,study_type_code,study_type_name,is_active,duration_seconds,external_motor_count,external_force_count,keyword_hits"

    On Error GoTo ExportError
    Set mgr = swModel.Extension.GetMotionStudyManager
    If mgr Is Nothing Then
        WriteTextFile outputPath, csv
        Exit Function
    End If

    names = mgr.GetMotionStudyNames
    If Not IsArray(names) Then
        WriteTextFile outputPath, csv
        Exit Function
    End If

    For i = LBound(names) To UBound(names)
        studyName = CStr(names(i))
        Set study = Nothing
        studyType = 0
        On Error Resume Next
        Set study = mgr.GetMotionStudy(studyName)
        If Not study Is Nothing Then studyType = CLng(study.StudyType)
        On Error GoTo ExportError

        AppendLine csv, CsvEscape(studyName) & "," & CsvEscape(CStr(studyType)) & "," & _
                        CsvEscape(MotionStudyTypeName(studyType)) & "," & _
                        CsvEscape(SafeProperty(study, "IsActive")) & "," & _
                        CsvEscape(SafeMethod(study, "GetDuration")) & "," & _
                        CsvEscape(SafeMethod(study, "GetNumOfExternalMotors")) & "," & _
                        CsvEscape(SafeMethod(study, "GetNumOfExternalForces")) & "," & _
                        CsvEscape(MetadataHits(studyName))
        ExportMotionStudies = ExportMotionStudies + 1
    Next i

    warnings.Add "motion_studies.csv inventories study tabs and basic properties. Driver keyframes, design-study variables, sensors, result plots, and monitor definitions may require a study-specific extractor."
    WriteTextFile outputPath, csv
    Exit Function

ExportError:
    warnings.Add "Motion-study API was unavailable or incomplete: " & Err.Description
    WriteTextFile outputPath, csv
End Function

Private Sub ExportManifestJson(ByVal swApp As Object, ByVal swModel As Object, _
                               ByVal outputDir As String, ByVal counts As Object, _
                               ByVal warnings As Collection)
    Dim json As String
    Dim sourcePath As String
    Dim baseVersion As String
    Dim currentVersion As String
    Dim hotFixes As String
    Dim revisionNumber As String
    Dim sourceSize As String
    Dim sourceModified As String
    Dim versionHistory As Variant

    sourcePath = SafeModelPath(swModel)
    On Error Resume Next
    revisionNumber = CStr(swApp.RevisionNumber)
    swApp.GetBuildNumbers2 baseVersion, currentVersion, hotFixes
    If Len(sourcePath) > 0 Then
        sourceSize = CStr(FileLen(sourcePath))
        sourceModified = Format$(FileDateTime(sourcePath), "yyyy-mm-dd\THH:nn:ss")
        versionHistory = swApp.VersionHistory(sourcePath)
    End If
    On Error GoTo 0

    AppendLine json, "{"
    AppendLine json, "  ""schema_version"": ""1.0.0"","
    AppendLine json, "  ""generated_at_local"": " & JsonString(Format$(Now, "yyyy-mm-dd\THH:nn:ss")) & ","
    AppendLine json, "  ""extractor"": {""name"": ""SW_Metadata_Exporter"", ""version"": " & _
                     JsonString(MACRO_VERSION) & ", ""read_only"": true},"
    AppendLine json, "  ""solidworks"": {"
    AppendLine json, "    ""revision_number"": " & JsonString(revisionNumber) & ","
    AppendLine json, "    ""base_version"": " & JsonString(baseVersion) & ","
    AppendLine json, "    ""build_number"": " & JsonString(currentVersion) & ","
    AppendLine json, "    ""hot_fixes"": " & JsonString(hotFixes)
    AppendLine json, "  },"
    AppendLine json, "  ""document"": {"
    AppendLine json, "    ""title"": " & JsonString(SafeModelTitle(swModel)) & ","
    AppendLine json, "    ""path"": " & JsonString(sourcePath) & ","
    AppendLine json, "    ""document_type_code"": " & CStr(swModel.GetType) & ","
    AppendLine json, "    ""document_type_name"": " & JsonString(DocumentTypeName(swModel.GetType)) & ","
    AppendLine json, "    ""file_size_bytes"": " & JsonString(sourceSize) & ","
    AppendLine json, "    ""file_modified_local"": " & JsonString(sourceModified) & ","
    AppendLine json, "    ""active_configuration"": " & JsonString(SafeActiveConfigurationName(swModel)) & ","
    AppendLine json, "    ""length_unit_code"": " & JsonString(SafeProperty(swModel, "LengthUnit")) & ","
    AppendLine json, "    ""version_history"": " & VariantToJsonArray(versionHistory)
    AppendLine json, "  },"
    AppendLine json, "  ""counts"": {"
    AppendLine json, "    ""configurations"": " & CountValue(counts, "configurations") & ","
    AppendLine json, "    ""custom_properties"": " & CountValue(counts, "custom_properties") & ","
    AppendLine json, "    ""equations"": " & CountValue(counts, "equations") & ","
    AppendLine json, "    ""external_references"": " & CountValue(counts, "external_references") & ","
    AppendLine json, "    ""components"": " & CountValue(counts, "components") & ","
    AppendLine json, "    ""features"": " & CountValue(counts, "features") & ","
    AppendLine json, "    ""dimensions"": " & CountValue(counts, "dimensions") & ","
    AppendLine json, "    ""motion_studies"": " & CountValue(counts, "motion_studies")
    AppendLine json, "  },"
    AppendLine json, "  ""warnings"": " & CollectionToJsonArray(warnings) & ","
    AppendLine json, "  ""limitations"": ["
    AppendLine json, "    ""The macro inspects only the active document and configuration state."","
    AppendLine json, "    ""Suppressed or lightweight component internals may not be loaded."","
    AppendLine json, "    ""Feature display-dimension enumeration is best-effort."","
    AppendLine json, "    ""Motion-study driver, monitor, sensor, keyframe, and result definitions may require a study-specific extractor."","
    AppendLine json, "    ""This package does not replace untouched native files, Pack and Go, Find References output, screenshots, or source hashes."""
    AppendLine json, "  ]"
    AppendLine json, "}"

    WriteTextFile JoinPath(outputDir, "solidworks_metadata.json"), json
End Sub

Private Sub ExportReadme(ByVal outputDir As String)
    Dim text As String
    AppendLine text, "SOLIDWORKS METADATA PACKAGE"
    AppendLine text, "==========================="
    AppendLine text, ""
    AppendLine text, "Start with solidworks_metadata.json. Detailed rows are stored in CSV files."
    AppendLine text, ""
    AppendLine text, "Search keyword_hits columns for: steer input, dimension2, ackermann, rack, tie rod, wheel, angle, sensor."
    AppendLine text, ""
    AppendLine text, "The macro does not save, rebuild, switch configuration, activate motion studies, resolve components, or change suppression state."
    AppendLine text, ""
    AppendLine text, "Supplement this package with the untouched SLDPRT/SLDASM, Pack and Go ZIP, File > Find References > Copy List, screenshots of configurations/equations/studies/external-reference status/rebuild warnings, and SHA-256 hashes of untouched downloaded bytes."
    WriteTextFile JoinPath(outputDir, "README.txt"), text
End Sub

Private Function SafeModelPath(ByVal swModel As Object) As String
    On Error Resume Next
    SafeModelPath = CStr(swModel.GetPathName)
    On Error GoTo 0
End Function

Private Function SafeModelTitle(ByVal swModel As Object) As String
    On Error Resume Next
    SafeModelTitle = CStr(swModel.GetTitle)
    On Error GoTo 0
End Function

Private Function SafeActiveConfigurationName(ByVal swModel As Object) As String
    Dim cfg As Object
    On Error Resume Next
    Set cfg = swModel.ConfigurationManager.ActiveConfiguration
    If Not cfg Is Nothing Then SafeActiveConfigurationName = CStr(cfg.Name)
    On Error GoTo 0
End Function

Private Function SafeProperty(ByVal obj As Object, ByVal propertyName As String) As String
    On Error Resume Next
    If obj Is Nothing Then Exit Function
    SafeProperty = CStr(CallByName(obj, propertyName, VbGet))
    On Error GoTo 0
End Function

Private Function SafeMethod(ByVal obj As Object, ByVal methodName As String) As String
    On Error Resume Next
    If obj Is Nothing Then Exit Function
    SafeMethod = CStr(CallByName(obj, methodName, VbMethod))
    On Error GoTo 0
End Function

Private Function SafeBoolMethod(ByVal obj As Object, ByVal methodName As String) As String
    On Error Resume Next
    If obj Is Nothing Then Exit Function
    SafeBoolMethod = BoolText(CBool(CallByName(obj, methodName, VbMethod)))
    On Error GoTo 0
End Function

Private Function DocumentTypeName(ByVal docType As Long) As String
    Select Case docType
        Case SW_DOC_PART: DocumentTypeName = "part"
        Case SW_DOC_ASSEMBLY: DocumentTypeName = "assembly"
        Case SW_DOC_DRAWING: DocumentTypeName = "drawing"
        Case Else: DocumentTypeName = "unknown"
    End Select
End Function

Private Function ComponentSuppressionName(ByVal stateCode As Long) As String
    Select Case stateCode
        Case 0: ComponentSuppressionName = "suppressed"
        Case 1: ComponentSuppressionName = "lightweight"
        Case 2: ComponentSuppressionName = "fully_resolved"
        Case 3: ComponentSuppressionName = "resolved"
        Case 4: ComponentSuppressionName = "fully_lightweight"
        Case 5: ComponentSuppressionName = "internal_id_mismatch"
        Case Else: ComponentSuppressionName = "unknown"
    End Select
End Function

Private Function ExternalReferenceStatusName(ByVal stateValue As Variant) As String
    Dim stateCode As Long
    On Error GoTo UnknownStatus
    stateCode = CLng(stateValue)
    Select Case stateCode
        Case SW_EXTREF_BROKEN: ExternalReferenceStatusName = "broken"
        Case SW_EXTREF_LOCKED: ExternalReferenceStatusName = "locked"
        Case SW_EXTREF_IN_CONTEXT: ExternalReferenceStatusName = "in_context"
        Case SW_EXTREF_OUT_OF_CONTEXT: ExternalReferenceStatusName = "out_of_context"
        Case SW_EXTREF_DANGLING: ExternalReferenceStatusName = "dangling"
        Case Else: ExternalReferenceStatusName = "unknown"
    End Select
    Exit Function
UnknownStatus:
    ExternalReferenceStatusName = "unknown"
End Function

Private Function MotionStudyTypeName(ByVal studyType As Long) As String
    Dim labels As String
    If (studyType And 1) <> 0 Then labels = AddPipe(labels, "animation")
    If (studyType And 2) <> 0 Then labels = AddPipe(labels, "basic_motion")
    If (studyType And 4) <> 0 Then labels = AddPipe(labels, "motion_analysis")
    If (studyType And 8) <> 0 Then labels = AddPipe(labels, "legacy_cosmos_motion")
    If (studyType And 16) <> 0 Then labels = AddPipe(labels, "simulation_or_new_motion")
    If Len(labels) = 0 Then labels = "not_motion_or_unknown"
    MotionStudyTypeName = labels
End Function

Private Function SafeVariantAt(ByVal value As Variant, ByVal zeroBasedIndex As Long) As Variant
    On Error GoTo MissingValue
    If IsArray(value) Then
        SafeVariantAt = value(LBound(value) + zeroBasedIndex)
    ElseIf zeroBasedIndex = 0 Then
        SafeVariantAt = value
    Else
        SafeVariantAt = ""
    End If
    Exit Function
MissingValue:
    SafeVariantAt = ""
End Function

Private Function VariantArrayCount(ByVal value As Variant) As Long
    On Error GoTo NoArray
    If IsArray(value) Then
        VariantArrayCount = UBound(value) - LBound(value) + 1
    ElseIf Not IsEmpty(value) And Not IsNull(value) Then
        VariantArrayCount = 1
    End If
    Exit Function
NoArray:
    VariantArrayCount = 0
End Function

Private Function MaximumVariantArrayCount(ByVal values As Variant) As Long
    Dim i As Long
    Dim thisCount As Long
    If Not IsArray(values) Then Exit Function
    For i = LBound(values) To UBound(values)
        thisCount = VariantArrayCount(values(i))
        If thisCount > MaximumVariantArrayCount Then MaximumVariantArrayCount = thisCount
    Next i
End Function

Private Function JoinVariant(ByVal value As Variant, ByVal delimiter As String) As String
    Dim i As Long
    Dim result As String
    On Error GoTo JoinFailed
    If IsArray(value) Then
        For i = LBound(value) To UBound(value)
            If Len(result) > 0 Then result = result & delimiter
            result = result & CStr(value(i))
        Next i
    ElseIf Not IsEmpty(value) And Not IsNull(value) Then
        result = CStr(value)
    End If
    JoinVariant = result
    Exit Function
JoinFailed:
    JoinVariant = ""
End Function

Private Function CsvEscape(ByVal value As String) As String
    Dim q As String
    q = Chr$(34)
    CsvEscape = q & Replace$(value, q, q & q) & q
End Function

Private Function JsonString(ByVal value As String) As String
    JsonString = Chr$(34) & JsonEscape(value) & Chr$(34)
End Function

Private Function JsonEscape(ByVal value As String) As String
    Dim result As String
    Dim bs As String
    Dim q As String

    bs = Chr$(92)
    q = Chr$(34)
    result = value
    result = Replace$(result, bs, bs & bs)
    result = Replace$(result, q, bs & q)
    result = Replace$(result, vbCrLf, bs & "n")
    result = Replace$(result, vbCr, bs & "n")
    result = Replace$(result, vbLf, bs & "n")
    result = Replace$(result, vbTab, bs & "t")
    JsonEscape = result
End Function

Private Function VariantToJsonArray(ByVal value As Variant) As String
    Dim result As String
    Dim i As Long
    result = "["
    On Error GoTo EmptyArray
    If IsArray(value) Then
        For i = LBound(value) To UBound(value)
            If i > LBound(value) Then result = result & ", "
            result = result & JsonString(CStr(value(i)))
        Next i
    ElseIf Not IsEmpty(value) And Not IsNull(value) Then
        result = result & JsonString(CStr(value))
    End If
    VariantToJsonArray = result & "]"
    Exit Function
EmptyArray:
    VariantToJsonArray = "[]"
End Function

Private Function CollectionToJsonArray(ByVal values As Collection) As String
    Dim result As String
    Dim i As Long
    result = "["
    For i = 1 To values.Count
        If i > 1 Then result = result & ", "
        result = result & JsonString(CStr(values(i)))
    Next i
    CollectionToJsonArray = result & "]"
End Function

Private Function BoolText(ByVal value As Boolean) As String
    If value Then BoolText = "true" Else BoolText = "false"
End Function

Private Function VariantToBoolean(ByVal value As Variant) As Boolean
    On Error Resume Next
    VariantToBoolean = CBool(value)
    On Error GoTo 0
End Function

Private Function CountValue(ByVal counts As Object, ByVal key As String) As String
    If counts.Exists(key) Then CountValue = CStr(counts(key)) Else CountValue = "0"
End Function

Private Function AddPipe(ByVal existing As String, ByVal newValue As String) As String
    If Len(existing) = 0 Then AddPipe = newValue Else AddPipe = existing & "|" & newValue
End Function

Private Function MetadataHits(ByVal text As String) As String
    Dim keywords As Variant
    Dim keyword As Variant
    Dim lowerText As String
    Dim result As String

    keywords = Array("steer input", "dimension2", "ackermann", "rack", "tie rod", _
                     "wheel", "motion", "study", "sensor", "angle", "geometry", _
                     "configuration", "design table")
    lowerText = LCase$(text)

    For Each keyword In keywords
        If InStr(1, lowerText, CStr(keyword), vbTextCompare) > 0 Then
            result = AddPipe(result, CStr(keyword))
        End If
    Next keyword
    MetadataHits = result
End Function
