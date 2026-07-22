Attribute VB_Name = "WUFR26_Metadata_Exporter"
Option Explicit

' WUFR-26 SOLIDWORKS metadata exporter
' Version 1.0.0
'
' Read-only intent:
' - Does not save or rebuild the active document.
' - Does not switch configurations or activate motion studies.
' - Does not resolve lightweight components.
' - Does not edit equations, design tables, references, or properties.
'
' Run this macro once with the intended parent steering assembly active and
' again with GEOMETRY FINAL.SLDPRT active. Load the SOLIDWORKS Motion add-in
' before running when motion-study metadata is required.

Private Const EXTRACTOR_NAME As String = "WUFR26_SOLIDWORKS_METADATA_EXPORTER"
Private Const EXTRACTOR_VERSION As String = "1.0.0"
Private Const MAX_FEATURES As Long = 25000
Private Const MAX_COMPONENTS As Long = 75000

Private Const DOC_PART As Long = 1
Private Const DOC_ASSEMBLY As Long = 2
Private Const DOC_DRAWING As Long = 3

Private gWarnings As Collection
Private gHits As Collection
Private gVisitedFeatures As Object
Private gFeatureCount As Long
Private gComponentCount As Long
Private gLightweightWarningAdded As Boolean

Public Sub main()
    On Error GoTo FatalError

    Dim swApp As Object
    Dim swModel As Object
    Dim outputPath As String
    Dim report As String
    Dim dirtyBefore As Boolean
    Dim dirtyAfter As Boolean

    Set swApp = Application.SldWorks
    Set swModel = swApp.ActiveDoc

    If swModel Is Nothing Then
        MsgBox "Open the steering assembly or GEOMETRY FINAL.SLDPRT and run the macro again.", _
               vbExclamation, EXTRACTOR_NAME
        Exit Sub
    End If

    Set gWarnings = New Collection
    Set gHits = New Collection
    Set gVisitedFeatures = CreateObject("Scripting.Dictionary")
    gFeatureCount = 0
    gComponentCount = 0
    gLightweightWarningAdded = False

    dirtyBefore = SafeGetSaveFlag(swModel)
    report = BuildReport(swApp, swModel, dirtyBefore, dirtyAfter)
    outputPath = DetermineOutputPath(swModel)
    WriteUtf8File outputPath, report

    Dim summary As String
    summary = "Metadata export complete." & vbCrLf & vbCrLf & outputPath & vbCrLf & vbCrLf & _
              "Warnings recorded: " & CStr(gWarnings.Count) & vbCrLf & _
              "Features recorded: " & CStr(gFeatureCount) & vbCrLf & _
              "Components recorded: " & CStr(gComponentCount)

    If dirtyAfter <> dirtyBefore Then
        summary = summary & vbCrLf & vbCrLf & _
                  "CAUTION: The document dirty flag changed while the macro ran. " & _
                  "The macro did not issue a save or rebuild command. Review the warnings."
    End If

    MsgBox summary, vbInformation, EXTRACTOR_NAME
    Exit Sub

FatalError:
    MsgBox "Metadata export failed: " & CStr(Err.Number) & " - " & Err.Description, _
           vbCritical, EXTRACTOR_NAME
End Sub

Private Function BuildReport(ByVal swApp As Object, ByVal swModel As Object, _
                             ByVal dirtyBefore As Boolean, ByRef dirtyAfter As Boolean) As String
    On Error GoTo Fail

    Dim applicationJson As String
    Dim documentJson As String
    Dim unitsJson As String
    Dim propertiesJson As String
    Dim configurationsJson As String
    Dim equationsJson As String
    Dim designTableJson As String
    Dim featuresJson As String
    Dim whatsWrongJson As String
    Dim dependenciesJson As String
    Dim externalReferencesJson As String
    Dim componentsJson As String
    Dim motionStudiesJson As String

    applicationJson = BuildApplicationJson(swApp)
    documentJson = BuildDocumentJson(swModel, dirtyBefore)
    unitsJson = BuildUnitsJson(swModel)
    propertiesJson = BuildCustomPropertiesJson(GetDocumentPropertyManager(swModel), "document")
    configurationsJson = BuildConfigurationsJson(swModel)
    equationsJson = BuildEquationsJson(swModel)
    designTableJson = BuildDesignTableJson(swModel)
    featuresJson = BuildFeaturesJson(swModel)
    whatsWrongJson = BuildWhatsWrongJson(swModel)
    dependenciesJson = BuildDependenciesJson(swModel)
    externalReferencesJson = BuildExternalReferencesJson(swModel)
    componentsJson = BuildComponentsJson(swModel)
    motionStudiesJson = BuildMotionStudiesJson(swModel)

    dirtyAfter = SafeGetSaveFlag(swModel)

    BuildReport = "{" & vbCrLf & _
        Indent(1) & Q("schema_version") & ": " & Q("1.0.0") & "," & vbCrLf & _
        Indent(1) & Q("extractor") & ": {" & _
            Q("name") & ": " & Q(EXTRACTOR_NAME) & ", " & _
            Q("version") & ": " & Q(EXTRACTOR_VERSION) & ", " & _
            Q("generated_local") & ": " & Q(LocalIsoTimestamp()) & ", " & _
            Q("read_only_intent") & ": true" & _
        "}," & vbCrLf & _
        Indent(1) & Q("application") & ": " & applicationJson & "," & vbCrLf & _
        Indent(1) & Q("document") & ": " & AddDirtyAfter(documentJson, dirtyAfter) & "," & vbCrLf & _
        Indent(1) & Q("units") & ": " & unitsJson & "," & vbCrLf & _
        Indent(1) & Q("document_custom_properties") & ": " & propertiesJson & "," & vbCrLf & _
        Indent(1) & Q("configurations") & ": " & configurationsJson & "," & vbCrLf & _
        Indent(1) & Q("equations") & ": " & equationsJson & "," & vbCrLf & _
        Indent(1) & Q("design_table") & ": " & designTableJson & "," & vbCrLf & _
        Indent(1) & Q("features") & ": " & featuresJson & "," & vbCrLf & _
        Indent(1) & Q("whats_wrong") & ": " & whatsWrongJson & "," & vbCrLf & _
        Indent(1) & Q("dependencies") & ": " & dependenciesJson & "," & vbCrLf & _
        Indent(1) & Q("external_references") & ": " & externalReferencesJson & "," & vbCrLf & _
        Indent(1) & Q("assembly_components") & ": " & componentsJson & "," & vbCrLf & _
        Indent(1) & Q("motion_studies") & ": " & motionStudiesJson & "," & vbCrLf & _
        Indent(1) & Q("target_name_matches") & ": " & CollectionToJsonArray(gHits) & "," & vbCrLf & _
        Indent(1) & Q("warnings") & ": " & StringCollectionToJsonArray(gWarnings) & vbCrLf & _
        "}"
    Exit Function

Fail:
    AddWarning "BuildReport failed: " & CStr(Err.Number) & " - " & Err.Description
    dirtyAfter = SafeGetSaveFlag(swModel)
    BuildReport = "{" & Q("fatal_error") & ": " & Q(Err.Description) & "}"
End Function

Private Function BuildApplicationJson(ByVal swApp As Object) As String
    On Error GoTo Fail

    Dim revision As String
    Dim baseVersion As Long
    Dim currentBuild As Long
    Dim hotfix As Long
    Dim buildAvailable As Boolean

    revision = ""
    On Error Resume Next
    revision = CStr(swApp.RevisionNumber())
    If Err.Number <> 0 Then
        AddWarning "Could not read ISldWorks.RevisionNumber: " & Err.Description
        Err.Clear
    End If

    swApp.GetBuildNumbers2 baseVersion, currentBuild, hotfix
    If Err.Number = 0 Then
        buildAvailable = True
    Else
        buildAvailable = False
        Err.Clear
    End If
    On Error GoTo Fail

    BuildApplicationJson = "{" & _
        Q("revision_number") & ": " & Q(revision) & ", " & _
        Q("build_numbers_available") & ": " & JsonBoolean(buildAvailable) & ", " & _
        Q("base_version") & ": " & JsonLongOrNull(baseVersion, buildAvailable) & ", " & _
        Q("current_build") & ": " & JsonLongOrNull(currentBuild, buildAvailable) & ", " & _
        Q("hotfix") & ": " & JsonLongOrNull(hotfix, buildAvailable) & _
        "}"
    Exit Function

Fail:
    AddWarning "Application metadata failed: " & CStr(Err.Number) & " - " & Err.Description
    BuildApplicationJson = "{}"
End Function

Private Function BuildDocumentJson(ByVal swModel As Object, ByVal dirtyBefore As Boolean) As String
    On Error GoTo Fail

    Dim docType As Long
    Dim activeConfiguration As String
    Dim title As String
    Dim pathName As String

    docType = CLng(swModel.GetType)
    title = CStr(swModel.GetTitle)
    pathName = CStr(swModel.GetPathName)
    activeConfiguration = GetActiveConfigurationName(swModel)

    AddSearchHits "document", pathName, title & " " & pathName & " " & activeConfiguration

    BuildDocumentJson = "{" & _
        Q("title") & ": " & Q(title) & ", " & _
        Q("path") & ": " & Q(pathName) & ", " & _
        Q("document_type_code") & ": " & CStr(docType) & ", " & _
        Q("document_type") & ": " & Q(DocumentTypeText(docType)) & ", " & _
        Q("active_configuration") & ": " & Q(activeConfiguration) & ", " & _
        Q("dirty_before") & ": " & JsonBoolean(dirtyBefore) & _
        "}"
    Exit Function

Fail:
    AddWarning "Document metadata failed: " & CStr(Err.Number) & " - " & Err.Description
    BuildDocumentJson = "{}"
End Function

Private Function AddDirtyAfter(ByVal documentJson As String, ByVal dirtyAfter As Boolean) As String
    If Right$(documentJson, 1) = "}" Then
        AddDirtyAfter = Left$(documentJson, Len(documentJson) - 1) & ", " & _
                        Q("dirty_after") & ": " & JsonBoolean(dirtyAfter) & "}"
    Else
        AddDirtyAfter = documentJson
    End If
End Function

Private Function BuildUnitsJson(ByVal swModel As Object) As String
    On Error GoTo Fail

    Dim values As Variant
    Dim i As Long
    Dim rawItems As Collection
    Set rawItems = New Collection

    values = swModel.GetUnits
    If IsUsableArray(values) Then
        For i = LBound(values) To UBound(values)
            rawItems.Add CStr(CLng(values(i)))
        Next i
    Else
        AddWarning "IModelDoc2.GetUnits returned no usable array."
    End If

    BuildUnitsJson = "{" & _
        Q("get_units_raw") & ": " & CollectionToJsonArray(rawItems) & ", " & _
        Q("field_order") & ": [" & _
            Q("length_unit") & ", " & Q("fraction_base") & ", " & _
            Q("fraction_value") & ", " & Q("significant_digits") & ", " & _
            Q("round_to_fraction") & _
        "]" & _
        "}"
    Exit Function

Fail:
    AddWarning "Unit metadata failed: " & CStr(Err.Number) & " - " & Err.Description
    BuildUnitsJson = "{}"
End Function

Private Function BuildConfigurationsJson(ByVal swModel As Object) As String
    On Error GoTo Fail

    Dim names As Variant
    Dim i As Long
    Dim j As Long
    Dim items As Collection
    Dim cfg As Object
    Dim cfgName As String
    Dim activeName As String
    Dim displayStates As Variant
    Dim displayItems As Collection
    Dim cfgProps As String

    Set items = New Collection
    activeName = GetActiveConfigurationName(swModel)
    names = swModel.GetConfigurationNames

    If Not IsUsableArray(names) Then
        AddWarning "No configuration-name array was returned."
        BuildConfigurationsJson = "[]"
        Exit Function
    End If

    For i = LBound(names) To UBound(names)
        cfgName = CStr(names(i))
        Set cfg = Nothing
        On Error Resume Next
        Set cfg = swModel.GetConfigurationByName(cfgName)
        If Err.Number <> 0 Then
            AddWarning "Could not read configuration '" & cfgName & "': " & Err.Description
            Err.Clear
        End If
        On Error GoTo Fail

        If Not cfg Is Nothing Then
            Set displayItems = New Collection
            On Error Resume Next
            displayStates = cfg.GetDisplayStates()
            If Err.Number = 0 And IsUsableArray(displayStates) Then
                For j = LBound(displayStates) To UBound(displayStates)
                    displayItems.Add Q(CStr(displayStates(j)))
                Next j
            Else
                Err.Clear
            End If
            On Error GoTo Fail

            cfgProps = BuildCustomPropertiesJson(GetConfigurationPropertyManager(swModel, cfgName), cfgName)
            items.Add "{" & _
                Q("name") & ": " & Q(cfgName) & ", " & _
                Q("active") & ": " & JsonBoolean(StrComp(cfgName, activeName, vbTextCompare) = 0) & ", " & _
                Q("comment") & ": " & Q(SafeStringProperty(cfg, "Comment")) & ", " & _
                Q("alternate_name") & ": " & Q(SafeStringProperty(cfg, "AlternateName")) & ", " & _
                Q("is_derived") & ": " & JsonBoolean(SafeBooleanProperty(cfg, "IsDerived", False)) & ", " & _
                Q("display_states") & ": " & CollectionToJsonArray(displayItems) & ", " & _
                Q("custom_properties") & ": " & cfgProps & _
                "}"
        Else
            items.Add "{" & Q("name") & ": " & Q(cfgName) & ", " & _
                      Q("error") & ": " & Q("Configuration object unavailable") & "}"
        End If

        AddSearchHits "configuration", cfgName, cfgName
    Next i

    BuildConfigurationsJson = CollectionToJsonArray(items)
    Exit Function

Fail:
    AddWarning "Configuration metadata failed: " & CStr(Err.Number) & " - " & Err.Description
    BuildConfigurationsJson = CollectionToJsonArray(items)
End Function

Private Function GetDocumentPropertyManager(ByVal swModel As Object) As Object
    On Error GoTo Fail
    Set GetDocumentPropertyManager = swModel.Extension.CustomPropertyManager("")
    Exit Function
Fail:
    AddWarning "Document custom-property manager unavailable: " & Err.Description
    Set GetDocumentPropertyManager = Nothing
End Function

Private Function GetConfigurationPropertyManager(ByVal swModel As Object, ByVal cfgName As String) As Object
    On Error GoTo Fail
    Set GetConfigurationPropertyManager = swModel.Extension.CustomPropertyManager(cfgName)
    Exit Function
Fail:
    AddWarning "Configuration custom-property manager unavailable for '" & cfgName & "': " & Err.Description
    Set GetConfigurationPropertyManager = Nothing
End Function

Private Function BuildCustomPropertiesJson(ByVal propMgr As Object, ByVal scopeName As String) As String
    On Error GoTo Fail

    Dim names As Variant
    Dim items As Collection
    Dim i As Long
    Dim propName As String
    Dim rawValue As String
    Dim resolvedValue As String
    Dim wasResolved As Boolean
    Dim linked As Boolean
    Dim typeCode As Long
    Dim resultCode As Long
    Dim get6Worked As Boolean

    Set items = New Collection
    If propMgr Is Nothing Then
        BuildCustomPropertiesJson = "[]"
        Exit Function
    End If

    names = propMgr.GetNames
    If Not IsUsableArray(names) Then
        BuildCustomPropertiesJson = "[]"
        Exit Function
    End If

    For i = LBound(names) To UBound(names)
        propName = CStr(names(i))
        rawValue = ""
        resolvedValue = ""
        wasResolved = False
        linked = False
        resultCode = 0
        get6Worked = False

        On Error Resume Next
        resultCode = CLng(propMgr.Get6(propName, True, rawValue, resolvedValue, wasResolved, linked))
        If Err.Number = 0 Then
            get6Worked = True
        Else
            Err.Clear
            resultCode = CLng(propMgr.Get5(propName, True, rawValue, resolvedValue, wasResolved))
            If Err.Number <> 0 Then
                AddWarning "Could not read custom property '" & propName & "' in scope '" & _
                           scopeName & "': " & Err.Description
                Err.Clear
            End If
        End If
        typeCode = CLng(propMgr.GetType2(propName))
        If Err.Number <> 0 Then
            typeCode = -1
            Err.Clear
        End If
        On Error GoTo Fail

        items.Add "{" & _
            Q("name") & ": " & Q(propName) & ", " & _
            Q("type_code") & ": " & CStr(typeCode) & ", " & _
            Q("raw_value") & ": " & Q(rawValue) & ", " & _
            Q("resolved_value") & ": " & Q(resolvedValue) & ", " & _
            Q("was_resolved") & ": " & JsonBoolean(wasResolved) & ", " & _
            Q("linked") & ": " & JsonBoolean(linked) & ", " & _
            Q("get6_used") & ": " & JsonBoolean(get6Worked) & ", " & _
            Q("result_code") & ": " & CStr(resultCode) & _
            "}"

        AddSearchHits "custom_property", scopeName & "/" & propName, _
                      propName & " " & rawValue & " " & resolvedValue
    Next i

    BuildCustomPropertiesJson = CollectionToJsonArray(items)
    Exit Function

Fail:
    AddWarning "Custom-property export failed for scope '" & scopeName & "': " & _
               CStr(Err.Number) & " - " & Err.Description
    BuildCustomPropertiesJson = CollectionToJsonArray(items)
End Function

Private Function BuildEquationsJson(ByVal swModel As Object) As String
    On Error GoTo Fail

    Dim eqMgr As Object
    Dim count As Long
    Dim i As Long
    Dim items As Collection
    Dim equationText As String
    Dim valueNumber As Double
    Dim valueAvailable As Boolean
    Dim isGlobal As Boolean
    Dim isDisabled As Boolean

    Set items = New Collection
    Set eqMgr = swModel.GetEquationMgr
    If eqMgr Is Nothing Then
        BuildEquationsJson = "[]"
        Exit Function
    End If

    count = CLng(eqMgr.GetCount)
    For i = 0 To count - 1
        equationText = ""
        valueNumber = 0#
        valueAvailable = False
        isGlobal = False
        isDisabled = False

        On Error Resume Next
        equationText = CStr(eqMgr.Equation(i))
        If Err.Number <> 0 Then
            equationText = ""
            Err.Clear
        End If
        valueNumber = CDbl(eqMgr.Value(i))
        If Err.Number = 0 Then
            valueAvailable = True
        Else
            Err.Clear
        End If
        isGlobal = CBool(eqMgr.GlobalVariable(i))
        If Err.Number <> 0 Then
            isGlobal = False
            Err.Clear
        End If
        isDisabled = CBool(eqMgr.Disabled(i))
        If Err.Number <> 0 Then
            isDisabled = False
            Err.Clear
        End If
        On Error GoTo Fail

        items.Add "{" & _
            Q("index") & ": " & CStr(i) & ", " & _
            Q("equation") & ": " & Q(equationText) & ", " & _
            Q("value") & ": " & JsonDoubleOrNull(valueNumber, valueAvailable) & ", " & _
            Q("global_variable") & ": " & JsonBoolean(isGlobal) & ", " & _
            Q("disabled") & ": " & JsonBoolean(isDisabled) & _
            "}"

        AddSearchHits "equation", "equation[" & CStr(i) & "]", equationText
    Next i

    BuildEquationsJson = CollectionToJsonArray(items)
    Exit Function

Fail:
    AddWarning "Equation export failed: " & CStr(Err.Number) & " - " & Err.Description
    BuildEquationsJson = CollectionToJsonArray(items)
End Function

Private Function BuildDesignTableJson(ByVal swModel As Object) As String
    On Error GoTo Fail

    Dim hasDesignTable As Boolean
    Dim tableObj As Object
    Dim tableAvailable As Boolean

    On Error Resume Next
    hasDesignTable = CBool(swModel.Extension.HasDesignTable)
    If Err.Number <> 0 Then Err.Clear
    If hasDesignTable Then
        Set tableObj = swModel.GetDesignTable
        If Err.Number = 0 And Not tableObj Is Nothing Then
            tableAvailable = True
        Else
            tableAvailable = False
            Err.Clear
        End If
    End If
    On Error GoTo Fail

    If tableAvailable Then
        BuildDesignTableJson = "{" & _
            Q("has_design_table") & ": true, " & _
            Q("object_available") & ": true, " & _
            Q("file_name") & ": " & Q(SafeStringProperty(tableObj, "FileName")) & ", " & _
            Q("source_type_code") & ": " & JsonSafeLongProperty(tableObj, "SourceType") & ", " & _
            Q("updatable") & ": " & JsonBoolean(SafeBooleanProperty(tableObj, "Updatable", False)) & _
            "}"
        AddSearchHits "design_table", "design_table", SafeStringProperty(tableObj, "FileName")
    Else
        BuildDesignTableJson = "{" & _
            Q("has_design_table") & ": " & JsonBoolean(hasDesignTable) & ", " & _
            Q("object_available") & ": false" & _
            "}"
    End If
    Exit Function

Fail:
    AddWarning "Design-table metadata failed: " & CStr(Err.Number) & " - " & Err.Description
    BuildDesignTableJson = "{}"
End Function

Private Function BuildFeaturesJson(ByVal swModel As Object) As String
    On Error GoTo Fail

    Dim items As Collection
    Dim firstFeature As Object

    Set items = New Collection
    Set firstFeature = swModel.FirstFeature
    CollectFeatureChain firstFeature, "", items

    BuildFeaturesJson = CollectionToJsonArray(items)
    Exit Function

Fail:
    AddWarning "Feature-tree export failed: " & CStr(Err.Number) & " - " & Err.Description
    BuildFeaturesJson = CollectionToJsonArray(items)
End Function

Private Sub CollectFeatureChain(ByVal firstFeature As Object, ByVal parentPath As String, _
                                ByVal items As Collection)
    On Error GoTo Fail

    Dim featureObj As Object
    Set featureObj = firstFeature

    Do While Not featureObj Is Nothing
        CollectSingleFeature featureObj, parentPath, items
        If gFeatureCount >= MAX_FEATURES Then Exit Do
        Set featureObj = featureObj.GetNextFeature
    Loop
    Exit Sub

Fail:
    AddWarning "Feature traversal failed under '" & parentPath & "': " & Err.Description
End Sub

Private Sub CollectSubFeatures(ByVal parentFeature As Object, ByVal parentPath As String, _
                               ByVal items As Collection)
    On Error GoTo Fail

    Dim child As Object
    Dim nextChild As Object

    Set child = parentFeature.GetFirstSubFeature
    Do While Not child Is Nothing
        Set nextChild = Nothing
        On Error Resume Next
        Set nextChild = child.GetNextSubFeature
        If Err.Number <> 0 Then Err.Clear
        On Error GoTo Fail

        CollectSingleFeature child, parentPath, items
        If gFeatureCount >= MAX_FEATURES Then Exit Do
        Set child = nextChild
    Loop
    Exit Sub

Fail:
    AddWarning "Subfeature traversal failed under '" & parentPath & "': " & Err.Description
End Sub

Private Sub CollectSingleFeature(ByVal featureObj As Object, ByVal parentPath As String, _
                                 ByVal items As Collection)
    On Error GoTo Fail

    If featureObj Is Nothing Then Exit Sub
    If gFeatureCount >= MAX_FEATURES Then
        AddWarningOnce "feature_limit", "Feature export stopped at MAX_FEATURES=" & CStr(MAX_FEATURES) & "."
        Exit Sub
    End If

    Dim pointerKey As String
    pointerKey = CStr(ObjPtr(featureObj))
    If gVisitedFeatures.Exists(pointerKey) Then Exit Sub
    gVisitedFeatures.Add pointerKey, True

    Dim featureName As String
    Dim typeName As String
    Dim featurePath As String
    Dim suppressed As Boolean
    Dim visibleCode As Long
    Dim frozen As Boolean
    Dim isWarning As Boolean
    Dim errorCode As Long
    Dim dimensionsJson As String

    featureName = SafeFeatureName(featureObj)
    typeName = SafeFeatureTypeName(featureObj)
    featurePath = JoinPath(parentPath, featureName)
    suppressed = SafeFeatureSuppressed(featureObj)
    visibleCode = SafeFeatureVisible(featureObj)
    frozen = SafeFeatureFrozen(featureObj)
    errorCode = SafeFeatureErrorCode(featureObj, isWarning)
    dimensionsJson = BuildFeatureDimensionsJson(featureObj, featurePath)

    items.Add "{" & _
        Q("path") & ": " & Q(featurePath) & ", " & _
        Q("name") & ": " & Q(featureName) & ", " & _
        Q("type_name") & ": " & Q(typeName) & ", " & _
        Q("suppressed_in_active_configuration") & ": " & JsonBoolean(suppressed) & ", " & _
        Q("visible_code") & ": " & CStr(visibleCode) & ", " & _
        Q("frozen") & ": " & JsonBoolean(frozen) & ", " & _
        Q("error_code") & ": " & CStr(errorCode) & ", " & _
        Q("is_warning") & ": " & JsonBoolean(isWarning) & ", " & _
        Q("dimensions") & ": " & dimensionsJson & _
        "}"

    gFeatureCount = gFeatureCount + 1
    AddSearchHits "feature", featurePath, featureName & " " & typeName
    CollectSubFeatures featureObj, featurePath, items
    Exit Sub

Fail:
    AddWarning "Feature export failed under '" & parentPath & "': " & _
               CStr(Err.Number) & " - " & Err.Description
End Sub

Private Function BuildFeatureDimensionsJson(ByVal featureObj As Object, ByVal featurePath As String) As String
    On Error GoTo Fail

    Dim items As Collection
    Dim displayDimension As Object
    Dim dimensionObj As Object
    Dim fullName As String
    Dim shortName As String
    Dim selectionName As String
    Dim valueNumber As Double
    Dim valueAvailable As Boolean
    Dim guard As Long

    Set items = New Collection
    Set displayDimension = featureObj.GetFirstDisplayDimension

    Do While Not displayDimension Is Nothing
        guard = guard + 1
        If guard > 10000 Then
            AddWarning "Dimension traversal guard reached for feature '" & featurePath & "'."
            Exit Do
        End If

        Set dimensionObj = Nothing
        fullName = ""
        shortName = ""
        selectionName = ""
        valueAvailable = False

        On Error Resume Next
        Set dimensionObj = displayDimension.GetDimension2(0)
        If Err.Number <> 0 Then Err.Clear
        If Not dimensionObj Is Nothing Then
            fullName = CStr(dimensionObj.FullName)
            If Err.Number <> 0 Then
                fullName = ""
                Err.Clear
            End If
            shortName = CStr(dimensionObj.Name)
            If Err.Number <> 0 Then
                shortName = ""
                Err.Clear
            End If
            valueNumber = CDbl(dimensionObj.SystemValue)
            If Err.Number = 0 Then
                valueAvailable = True
            Else
                Err.Clear
            End If
        End If
        selectionName = CStr(displayDimension.GetNameForSelection)
        If Err.Number <> 0 Then
            selectionName = ""
            Err.Clear
        End If
        On Error GoTo Fail

        items.Add "{" & _
            Q("full_name") & ": " & Q(fullName) & ", " & _
            Q("name") & ": " & Q(shortName) & ", " & _
            Q("selection_name") & ": " & Q(selectionName) & ", " & _
            Q("system_value_si") & ": " & JsonDoubleOrNull(valueNumber, valueAvailable) & _
            "}"

        AddSearchHits "dimension", featurePath & "/" & fullName, _
                      fullName & " " & shortName & " " & selectionName
        Set displayDimension = featureObj.GetNextDisplayDimension(displayDimension)
    Loop

    BuildFeatureDimensionsJson = CollectionToJsonArray(items)
    Exit Function

Fail:
    AddWarning "Dimension export failed for feature '" & featurePath & "': " & Err.Description
    BuildFeatureDimensionsJson = CollectionToJsonArray(items)
End Function

Private Function BuildWhatsWrongJson(ByVal swModel As Object) As String
    On Error GoTo Fail

    Dim ext As Object
    Dim count As Long
    Dim featureArray As Variant
    Dim errorArray As Variant
    Dim warningArray As Variant
    Dim ok As Boolean
    Dim items As Collection
    Dim i As Long
    Dim featureObj As Object

    Set items = New Collection
    Set ext = swModel.Extension
    count = CLng(ext.GetWhatsWrongCount)
    If count <= 0 Then
        BuildWhatsWrongJson = "[]"
        Exit Function
    End If

    ok = CBool(ext.GetWhatsWrong(featureArray, errorArray, warningArray))
    If Not ok Then
        AddWarning "GetWhatsWrongCount reported " & CStr(count) & _
                   " item(s), but GetWhatsWrong returned False."
        BuildWhatsWrongJson = "[]"
        Exit Function
    End If

    If IsUsableArray(errorArray) Then
        For i = LBound(errorArray) To UBound(errorArray)
            Set featureObj = Nothing
            If IsUsableArray(featureArray) Then
                If i >= LBound(featureArray) And i <= UBound(featureArray) Then
                    On Error Resume Next
                    Set featureObj = featureArray(i)
                    Err.Clear
                    On Error GoTo Fail
                End If
            End If

            items.Add "{" & _
                Q("feature_name") & ": " & Q(SafeFeatureName(featureObj)) & ", " & _
                Q("feature_type") & ": " & Q(SafeFeatureTypeName(featureObj)) & ", " & _
                Q("error_code") & ": " & CStr(CLng(errorArray(i))) & ", " & _
                Q("is_warning") & ": " & JsonBoolean(ArrayBooleanAt(warningArray, i)) & _
                "}"
        Next i
    End If

    BuildWhatsWrongJson = CollectionToJsonArray(items)
    Exit Function

Fail:
    AddWarning "What's Wrong export failed: " & CStr(Err.Number) & " - " & Err.Description
    BuildWhatsWrongJson = CollectionToJsonArray(items)
End Function

Private Function BuildDependenciesJson(ByVal swModel As Object) As String
    On Error GoTo Fail

    Dim dependencies As Variant
    Dim items As Collection
    Dim i As Long
    Dim methodUsed As String
    Dim ext As Object

    Set items = New Collection
    Set ext = swModel.Extension

    On Error Resume Next
    dependencies = ext.GetDependencies(True, True, False, True, True)
    If Err.Number = 0 And IsUsableArray(dependencies) Then
        methodUsed = "IModelDocExtension.GetDependencies"
    Else
        Err.Clear
        dependencies = swModel.GetDependencies2(True, True, False)
        If Err.Number = 0 And IsUsableArray(dependencies) Then
            methodUsed = "IModelDoc2.GetDependencies2"
        Else
            methodUsed = ""
            Err.Clear
        End If
    End If
    On Error GoTo Fail

    If IsUsableArray(dependencies) Then
        i = LBound(dependencies)
        Do While i <= UBound(dependencies)
            If i + 1 <= UBound(dependencies) Then
                items.Add "{" & _
                    Q("display_name") & ": " & Q(CStr(dependencies(i))) & ", " & _
                    Q("resolved_path") & ": " & Q(CStr(dependencies(i + 1))) & _
                    "}"
                AddSearchHits "dependency", CStr(dependencies(i + 1)), _
                              CStr(dependencies(i)) & " " & CStr(dependencies(i + 1))
                i = i + 2
            Else
                items.Add "{" & Q("unpaired_value") & ": " & Q(CStr(dependencies(i))) & "}"
                i = i + 1
            End If
        Loop
    End If

    BuildDependenciesJson = "{" & _
        Q("method") & ": " & Q(methodUsed) & ", " & _
        Q("items") & ": " & CollectionToJsonArray(items) & _
        "}"
    Exit Function

Fail:
    AddWarning "Dependency export failed: " & CStr(Err.Number) & " - " & Err.Description
    BuildDependenciesJson = "{" & Q("items") & ": []}"
End Function

Private Function BuildExternalReferencesJson(ByVal swModel As Object) As String
    On Error GoTo Fail

    Dim ext As Object
    Dim count As Long
    Dim modelPaths As Variant
    Dim componentPaths As Variant
    Dim featureNames As Variant
    Dim dataTypes As Variant
    Dim statuses As Variant
    Dim refEntities As Variant
    Dim featureComponents As Variant
    Dim configOptions As Variant
    Dim configNames As Variant
    Dim items As Collection
    Dim i As Long

    Set items = New Collection
    Set ext = swModel.Extension

    On Error Resume Next
    count = CLng(ext.ListExternalFileReferencesCount)
    If Err.Number <> 0 Then
        AddWarning "Model-level external-reference API is unavailable. " & _
                   "Use the External References screenshots and Find References list as supplements."
        Err.Clear
        BuildExternalReferencesJson = "{" & _
            Q("api_available") & ": false, " & Q("count") & ": 0, " & Q("items") & ": []}"
        Exit Function
    End If

    If count > 0 Then
        ext.ListExternalFileReferences2 modelPaths, componentPaths, featureNames, dataTypes, _
                                        statuses, refEntities, featureComponents, configOptions, configNames
        If Err.Number <> 0 Then
            AddWarning "ListExternalFileReferences2 failed: " & Err.Description
            Err.Clear
            BuildExternalReferencesJson = "{" & _
                Q("api_available") & ": true, " & Q("count") & ": " & CStr(count) & ", " & _
                Q("items") & ": [], " & Q("read_error") & ": true}"
            Exit Function
        End If
    End If
    On Error GoTo Fail

    If count > 0 And IsUsableArray(modelPaths) Then
        For i = LBound(modelPaths) To UBound(modelPaths)
            items.Add "{" & _
                Q("model_path") & ": " & Q(ArrayStringAt(modelPaths, i)) & ", " & _
                Q("component_path") & ": " & Q(ArrayStringAt(componentPaths, i)) & ", " & _
                Q("feature_name") & ": " & Q(ArrayStringAt(featureNames, i)) & ", " & _
                Q("data_type") & ": " & Q(ArrayStringAt(dataTypes, i)) & ", " & _
                Q("status_code") & ": " & CStr(ArrayLongAt(statuses, i, -1)) & ", " & _
                Q("status") & ": " & Q(ExternalReferenceStatusText(ArrayLongAt(statuses, i, -1))) & ", " & _
                Q("referenced_entity") & ": " & Q(ArrayStringAt(refEntities, i)) & ", " & _
                Q("feature_component") & ": " & Q(ArrayStringAt(featureComponents, i)) & ", " & _
                Q("configuration_option_code") & ": " & CStr(ArrayLongAt(configOptions, i, -1)) & ", " & _
                Q("configuration_name") & ": " & Q(ArrayStringAt(configNames, i)) & _
                "}"

            AddSearchHits "external_reference", ArrayStringAt(modelPaths, i), _
                          ArrayStringAt(featureNames, i) & " " & ArrayStringAt(modelPaths, i)
        Next i
    End If

    BuildExternalReferencesJson = "{" & _
        Q("api_available") & ": true, " & _
        Q("count") & ": " & CStr(count) & ", " & _
        Q("items") & ": " & CollectionToJsonArray(items) & _
        "}"
    Exit Function

Fail:
    AddWarning "External-reference export failed: " & CStr(Err.Number) & " - " & Err.Description
    BuildExternalReferencesJson = "{" & _
        Q("api_available") & ": false, " & Q("count") & ": 0, " & Q("items") & ": []}"
End Function

Private Function BuildComponentsJson(ByVal swModel As Object) As String
    On Error GoTo Fail

    Dim componentArray As Variant
    Dim items As Collection
    Dim componentObj As Object
    Dim i As Long

    Set items = New Collection
    If CLng(swModel.GetType) <> DOC_ASSEMBLY Then
        BuildComponentsJson = "[]"
        Exit Function
    End If

    componentArray = swModel.GetComponents(False)
    If Not IsUsableArray(componentArray) Then
        BuildComponentsJson = "[]"
        Exit Function
    End If

    For i = LBound(componentArray) To UBound(componentArray)
        If gComponentCount >= MAX_COMPONENTS Then
            AddWarningOnce "component_limit", _
                           "Component export stopped at MAX_COMPONENTS=" & CStr(MAX_COMPONENTS) & "."
            Exit For
        End If

        Set componentObj = Nothing
        On Error Resume Next
        Set componentObj = componentArray(i)
        Err.Clear
        On Error GoTo Fail

        If Not componentObj Is Nothing Then
            items.Add BuildOneComponentJson(componentObj)
            gComponentCount = gComponentCount + 1
        End If
    Next i

    BuildComponentsJson = CollectionToJsonArray(items)
    Exit Function

Fail:
    AddWarning "Assembly-component export failed: " & CStr(Err.Number) & " - " & Err.Description
    BuildComponentsJson = CollectionToJsonArray(items)
End Function

Private Function BuildOneComponentJson(ByVal componentObj As Object) As String
    On Error GoTo Fail

    Dim nameText As String
    Dim pathText As String
    Dim refConfig As String
    Dim refDisplayState As String
    Dim suppressionCode As Long
    Dim isSuppressed As Boolean
    Dim isLightweight As Boolean
    Dim isEnvelope As Boolean
    Dim visibleCode As Long
    Dim isFixed As Boolean

    nameText = SafeStringProperty(componentObj, "Name2")
    pathText = SafeStringMethod0(componentObj, "GetPathName")
    refConfig = SafeStringProperty(componentObj, "ReferencedConfiguration")
    refDisplayState = SafeStringProperty(componentObj, "ReferencedDisplayState")
    suppressionCode = SafeLongMethod0(componentObj, "GetSuppression", -1)
    isSuppressed = SafeBooleanMethod0(componentObj, "IsSuppressed", False)
    isLightweight = SafeBooleanMethod0(componentObj, "IsLightWeight", False)
    isEnvelope = SafeBooleanMethod0(componentObj, "IsEnvelope", False)
    visibleCode = SafeLongProperty(componentObj, "Visible", -1)
    isFixed = SafeBooleanMethod0(componentObj, "IsFixed", False)

    If isLightweight And Not gLightweightWarningAdded Then
        AddWarning "One or more assembly components are lightweight. Component and external-reference " & _
                   "metadata may be incomplete; manually resolve the steering assembly and rerun."
        gLightweightWarningAdded = True
    End If

    AddSearchHits "component", pathText, nameText & " " & pathText & " " & refConfig

    BuildOneComponentJson = "{" & _
        Q("instance_name") & ": " & Q(nameText) & ", " & _
        Q("path") & ": " & Q(pathText) & ", " & _
        Q("referenced_configuration") & ": " & Q(refConfig) & ", " & _
        Q("referenced_display_state") & ": " & Q(refDisplayState) & ", " & _
        Q("suppression_code") & ": " & CStr(suppressionCode) & ", " & _
        Q("suppressed") & ": " & JsonBoolean(isSuppressed) & ", " & _
        Q("lightweight") & ": " & JsonBoolean(isLightweight) & ", " & _
        Q("envelope") & ": " & JsonBoolean(isEnvelope) & ", " & _
        Q("visible_code") & ": " & CStr(visibleCode) & ", " & _
        Q("fixed") & ": " & JsonBoolean(isFixed) & _
        "}"
    Exit Function

Fail:
    AddWarning "Component export failed: " & CStr(Err.Number) & " - " & Err.Description
    BuildOneComponentJson = "{" & Q("error") & ": " & Q(Err.Description) & "}"
End Function

Private Function BuildMotionStudiesJson(ByVal swModel As Object) As String
    On Error GoTo Fail

    Dim managerObj As Object
    Dim studyNames As Variant
    Dim items As Collection
    Dim i As Long
    Dim studyObj As Object

    Set items = New Collection
    Set managerObj = Nothing

    On Error Resume Next
    Set managerObj = swModel.Extension.GetMotionStudyManager()
    If Err.Number <> 0 Or managerObj Is Nothing Then
        AddWarning "Motion Study Manager unavailable. Load the SOLIDWORKS Motion add-in and rerun."
        Err.Clear
        BuildMotionStudiesJson = "{" & _
            Q("manager_available") & ": false, " & Q("items") & ": []}"
        Exit Function
    End If

    studyNames = managerObj.GetMotionStudyNames()
    If Err.Number <> 0 Then
        AddWarning "GetMotionStudyNames failed: " & Err.Description
        Err.Clear
    End If
    On Error GoTo Fail

    If IsUsableArray(studyNames) Then
        For i = LBound(studyNames) To UBound(studyNames)
            Set studyObj = Nothing
            On Error Resume Next
            Set studyObj = managerObj.GetMotionStudy(CStr(studyNames(i)))
            If Err.Number <> 0 Then
                AddWarning "Could not access motion study '" & CStr(studyNames(i)) & "': " & Err.Description
                Err.Clear
            End If
            On Error GoTo Fail

            If Not studyObj Is Nothing Then
                items.Add BuildOneMotionStudyJson(studyObj, CStr(studyNames(i)))
            Else
                items.Add "{" & Q("name") & ": " & Q(CStr(studyNames(i))) & ", " & _
                          Q("error") & ": " & Q("Study object unavailable") & "}"
            End If
        Next i
    End If

    BuildMotionStudiesJson = "{" & _
        Q("manager_available") & ": true, " & _
        Q("items") & ": " & CollectionToJsonArray(items) & _
        "}"
    Exit Function

Fail:
    AddWarning "Motion-study export failed: " & CStr(Err.Number) & " - " & Err.Description
    BuildMotionStudiesJson = "{" & _
        Q("manager_available") & ": false, " & Q("items") & ": []}"
End Function

Private Function BuildOneMotionStudyJson(ByVal studyObj As Object, ByVal studyName As String) As String
    On Error GoTo Fail

    Dim studyType As Long
    Dim duration As Double
    Dim durationAvailable As Boolean
    Dim timeBar As Double
    Dim timeBarAvailable As Boolean
    Dim featureCount As Long
    Dim externalMotorsForces As Long
    Dim propertiesObj As Object
    Dim frameRate As Double
    Dim frameRateAvailable As Boolean
    Dim featureItems As Collection
    Dim motionFeatures As Variant
    Dim i As Long
    Dim motionFeature As Object
    Dim featureName As String
    Dim featureType As String

    Set featureItems = New Collection
    studyType = SafeLongProperty(studyObj, "StudyType", -1)
    duration = SafeDoubleMethod0(studyObj, "GetDuration", durationAvailable)
    timeBar = SafeDoubleMethod0(studyObj, "GetTimeBar", timeBarAvailable)
    featureCount = SafeLongMethod0(studyObj, "GetMotionFeaturesCount", -1)
    externalMotorsForces = SafeLongMethod0(studyObj, "GetExternalMotorsAndForcesCount", -1)

    Set propertiesObj = Nothing
    On Error Resume Next
    Set propertiesObj = studyObj.GetProperties(studyType)
    If Err.Number <> 0 Then Err.Clear
    If Not propertiesObj Is Nothing Then
        frameRate = CDbl(propertiesObj.GetFrameRate())
        If Err.Number = 0 Then
            frameRateAvailable = True
        Else
            frameRateAvailable = False
            Err.Clear
        End If
    End If

    motionFeatures = studyObj.GetMotionFeatures()
    If Err.Number <> 0 Then Err.Clear
    On Error GoTo Fail

    If IsUsableArray(motionFeatures) Then
        For i = LBound(motionFeatures) To UBound(motionFeatures)
            Set motionFeature = Nothing
            On Error Resume Next
            Set motionFeature = motionFeatures(i)
            Err.Clear
            On Error GoTo Fail

            If Not motionFeature Is Nothing Then
                featureName = SafeFeatureName(motionFeature)
                featureType = SafeFeatureTypeName(motionFeature)
                featureItems.Add "{" & _
                    Q("name") & ": " & Q(featureName) & ", " & _
                    Q("type_name") & ": " & Q(featureType) & _
                    "}"
                AddSearchHits "motion_feature", studyName & "/" & featureName, _
                              featureName & " " & featureType
            End If
        Next i
    End If

    AddSearchHits "motion_study", studyName, studyName

    BuildOneMotionStudyJson = "{" & _
        Q("name") & ": " & Q(studyName) & ", " & _
        Q("study_type_code") & ": " & CStr(studyType) & ", " & _
        Q("duration_seconds") & ": " & JsonDoubleOrNull(duration, durationAvailable) & ", " & _
        Q("time_bar_seconds") & ": " & JsonDoubleOrNull(timeBar, timeBarAvailable) & ", " & _
        Q("frame_rate") & ": " & JsonDoubleOrNull(frameRate, frameRateAvailable) & ", " & _
        Q("motion_feature_count_reported") & ": " & CStr(featureCount) & ", " & _
        Q("external_motors_and_forces_count") & ": " & CStr(externalMotorsForces) & ", " & _
        Q("motion_features") & ": " & CollectionToJsonArray(featureItems) & _
        "}"
    Exit Function

Fail:
    AddWarning "Motion-study metadata failed for '" & studyName & "': " & _
               CStr(Err.Number) & " - " & Err.Description
    BuildOneMotionStudyJson = "{" & Q("name") & ": " & Q(studyName) & ", " & _
                              Q("error") & ": " & Q(Err.Description) & "}"
End Function

Private Sub AddSearchHits(ByVal sourceType As String, ByVal sourcePath As String, ByVal textValue As String)
    On Error GoTo Fail

    Dim terms As Variant
    Dim term As Variant
    terms = Array("steer input", "dimension2", "ackermann", "rack", "tie rod", _
                  "tierod", "wheel angle", "steering angle", "motion study")

    For Each term In terms
        If InStr(1, textValue, CStr(term), vbTextCompare) > 0 Then
            gHits.Add "{" & _
                Q("source_type") & ": " & Q(sourceType) & ", " & _
                Q("source_path") & ": " & Q(sourcePath) & ", " & _
                Q("matched_term") & ": " & Q(CStr(term)) & ", " & _
                Q("text") & ": " & Q(textValue) & _
                "}"
        End If
    Next term
    Exit Sub

Fail:
    AddWarning "Target-name matching failed at '" & sourcePath & "': " & Err.Description
End Sub

Private Function SafeGetSaveFlag(ByVal swModel As Object) As Boolean
    On Error GoTo Fail
    SafeGetSaveFlag = CBool(swModel.GetSaveFlag())
    Exit Function
Fail:
    AddWarning "Could not read document dirty flag: " & Err.Description
    SafeGetSaveFlag = False
End Function

Private Function GetActiveConfigurationName(ByVal swModel As Object) As String
    On Error GoTo Fail
    Dim cfg As Object
    Set cfg = swModel.ConfigurationManager.ActiveConfiguration
    If Not cfg Is Nothing Then GetActiveConfigurationName = CStr(cfg.Name)
    Exit Function
Fail:
    AddWarning "Could not read active configuration: " & Err.Description
    GetActiveConfigurationName = ""
End Function

Private Function SafeFeatureName(ByVal featureObj As Object) As String
    On Error GoTo Fail
    If Not featureObj Is Nothing Then SafeFeatureName = CStr(featureObj.Name)
    Exit Function
Fail:
    SafeFeatureName = ""
End Function

Private Function SafeFeatureTypeName(ByVal featureObj As Object) As String
    On Error GoTo Fail
    If Not featureObj Is Nothing Then
        SafeFeatureTypeName = CStr(featureObj.GetTypeName2)
        If Len(SafeFeatureTypeName) = 0 Then SafeFeatureTypeName = CStr(featureObj.GetTypeName)
    End If
    Exit Function
Fail:
    SafeFeatureTypeName = ""
End Function

Private Function SafeFeatureSuppressed(ByVal featureObj As Object) As Boolean
    On Error GoTo Fail
    SafeFeatureSuppressed = CBool(featureObj.IsSuppressed)
    Exit Function
Fail:
    SafeFeatureSuppressed = False
End Function

Private Function SafeFeatureVisible(ByVal featureObj As Object) As Long
    On Error GoTo Fail
    SafeFeatureVisible = CLng(featureObj.Visible)
    Exit Function
Fail:
    SafeFeatureVisible = -1
End Function

Private Function SafeFeatureFrozen(ByVal featureObj As Object) As Boolean
    On Error GoTo Fail
    SafeFeatureFrozen = CBool(featureObj.IsFrozen)
    Exit Function
Fail:
    SafeFeatureFrozen = False
End Function

Private Function SafeFeatureErrorCode(ByVal featureObj As Object, ByRef isWarning As Boolean) As Long
    On Error GoTo Fail
    isWarning = False
    SafeFeatureErrorCode = CLng(featureObj.GetErrorCode2(isWarning))
    Exit Function
Fail:
    isWarning = False
    SafeFeatureErrorCode = 0
End Function

Private Function SafeStringProperty(ByVal obj As Object, ByVal propertyName As String) As String
    On Error GoTo Fail
    If Not obj Is Nothing Then SafeStringProperty = CStr(CallByName(obj, propertyName, VbGet))
    Exit Function
Fail:
    SafeStringProperty = ""
End Function

Private Function SafeStringMethod0(ByVal obj As Object, ByVal methodName As String) As String
    On Error GoTo Fail
    If Not obj Is Nothing Then SafeStringMethod0 = CStr(CallByName(obj, methodName, VbMethod))
    Exit Function
Fail:
    SafeStringMethod0 = ""
End Function

Private Function SafeBooleanProperty(ByVal obj As Object, ByVal propertyName As String, _
                                     ByVal fallback As Boolean) As Boolean
    On Error GoTo Fail
    If obj Is Nothing Then
        SafeBooleanProperty = fallback
    Else
        SafeBooleanProperty = CBool(CallByName(obj, propertyName, VbGet))
    End If
    Exit Function
Fail:
    SafeBooleanProperty = fallback
End Function

Private Function SafeBooleanMethod0(ByVal obj As Object, ByVal methodName As String, _
                                    ByVal fallback As Boolean) As Boolean
    On Error GoTo Fail
    If obj Is Nothing Then
        SafeBooleanMethod0 = fallback
    Else
        SafeBooleanMethod0 = CBool(CallByName(obj, methodName, VbMethod))
    End If
    Exit Function
Fail:
    SafeBooleanMethod0 = fallback
End Function

Private Function SafeLongProperty(ByVal obj As Object, ByVal propertyName As String, _
                                  ByVal fallback As Long) As Long
    On Error GoTo Fail
    If obj Is Nothing Then
        SafeLongProperty = fallback
    Else
        SafeLongProperty = CLng(CallByName(obj, propertyName, VbGet))
    End If
    Exit Function
Fail:
    SafeLongProperty = fallback
End Function

Private Function SafeLongMethod0(ByVal obj As Object, ByVal methodName As String, _
                                 ByVal fallback As Long) As Long
    On Error GoTo Fail
    If obj Is Nothing Then
        SafeLongMethod0 = fallback
    Else
        SafeLongMethod0 = CLng(CallByName(obj, methodName, VbMethod))
    End If
    Exit Function
Fail:
    SafeLongMethod0 = fallback
End Function

Private Function SafeDoubleMethod0(ByVal obj As Object, ByVal methodName As String, _
                                   ByRef available As Boolean) As Double
    On Error GoTo Fail
    If obj Is Nothing Then GoTo Fail
    SafeDoubleMethod0 = CDbl(CallByName(obj, methodName, VbMethod))
    available = True
    Exit Function
Fail:
    available = False
    SafeDoubleMethod0 = 0#
End Function

Private Function JsonSafeLongProperty(ByVal obj As Object, ByVal propertyName As String) As String
    On Error GoTo Fail
    JsonSafeLongProperty = CStr(CLng(CallByName(obj, propertyName, VbGet)))
    Exit Function
Fail:
    JsonSafeLongProperty = "null"
End Function

Private Function DetermineOutputPath(ByVal swModel As Object) As String
    On Error GoTo Fail

    Dim modelPath As String
    Dim outputFolder As String
    Dim title As String
    Dim baseName As String

    modelPath = CStr(swModel.GetPathName)
    title = CStr(swModel.GetTitle)
    baseName = SanitizeFileName(RemoveExtension(title))

    If Len(modelPath) > 0 Then
        outputFolder = FolderFromPath(modelPath)
    Else
        outputFolder = CStr(CreateObject("WScript.Shell").SpecialFolders("Desktop"))
        AddWarning "The active document is unsaved; output was written to the Desktop."
    End If

    DetermineOutputPath = outputFolder & "\" & baseName & "_" & _
                          Format$(Now, "yyyymmdd_hhnnss") & "_solidworks_metadata.json"
    Exit Function

Fail:
    DetermineOutputPath = Environ$("TEMP") & "\solidworks_metadata_" & _
                          Format$(Now, "yyyymmdd_hhnnss") & ".json"
    AddWarning "Could not derive the preferred output path; using TEMP: " & Err.Description
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
    Err.Raise vbObjectError + 2100, EXTRACTOR_NAME, _
              "Could not write UTF-8 JSON file '" & filePath & "': " & Err.Description
End Sub

Private Sub AddWarning(ByVal message As String)
    On Error Resume Next
    If gWarnings Is Nothing Then Set gWarnings = New Collection
    gWarnings.Add message
End Sub

Private Sub AddWarningOnce(ByVal key As String, ByVal message As String)
    On Error Resume Next
    Static seen As Object
    If seen Is Nothing Then Set seen = CreateObject("Scripting.Dictionary")
    If Not seen.Exists(key) Then
        seen.Add key, True
        AddWarning message
    End If
End Sub

Private Function CollectionToJsonArray(ByVal items As Collection) As String
    Dim result As String
    Dim i As Long

    result = "["
    If Not items Is Nothing Then
        For i = 1 To items.Count
            If i > 1 Then result = result & ","
            result = result & vbCrLf & Indent(2) & CStr(items(i))
        Next i
        If items.Count > 0 Then result = result & vbCrLf & Indent(1)
    End If
    result = result & "]"
    CollectionToJsonArray = result
End Function

Private Function StringCollectionToJsonArray(ByVal items As Collection) As String
    Dim encoded As Collection
    Dim i As Long
    Set encoded = New Collection

    If Not items Is Nothing Then
        For i = 1 To items.Count
            encoded.Add Q(CStr(items(i)))
        Next i
    End If
    StringCollectionToJsonArray = CollectionToJsonArray(encoded)
End Function

Private Function Q(ByVal value As String) As String
    Q = Chr$(34) & JsonEscape(value) & Chr$(34)
End Function

Private Function JsonEscape(ByVal value As String) As String
    Dim result As String
    Dim i As Long
    Dim codePoint As Long
    Dim ch As String

    result = ""
    For i = 1 To Len(value)
        ch = Mid$(value, i, 1)
        codePoint = AscW(ch)
        If codePoint < 0 Then codePoint = codePoint + 65536

        Select Case codePoint
            Case 34
                result = result & "\" & Chr$(34)
            Case 92
                result = result & "\\"
            Case 8
                result = result & "\b"
            Case 9
                result = result & "\t"
            Case 10
                result = result & "\n"
            Case 12
                result = result & "\f"
            Case 13
                result = result & "\r"
            Case 0 To 31
                result = result & "\u" & Right$("0000" & Hex$(codePoint), 4)
            Case Else
                result = result & ch
        End Select
    Next i

    JsonEscape = result
End Function

Private Function JsonBoolean(ByVal value As Boolean) As String
    If value Then
        JsonBoolean = "true"
    Else
        JsonBoolean = "false"
    End If
End Function

Private Function JsonDoubleOrNull(ByVal value As Double, ByVal available As Boolean) As String
    If available Then
        JsonDoubleOrNull = InvariantNumber(value)
    Else
        JsonDoubleOrNull = "null"
    End If
End Function

Private Function JsonLongOrNull(ByVal value As Long, ByVal available As Boolean) As String
    If available Then
        JsonLongOrNull = CStr(value)
    Else
        JsonLongOrNull = "null"
    End If
End Function

Private Function InvariantNumber(ByVal value As Double) As String
    Dim textValue As String
    textValue = Trim$(Str$(value))
    textValue = Replace$(textValue, ",", ".")
    If textValue = "-0" Then textValue = "0"
    InvariantNumber = textValue
End Function

Private Function Indent(ByVal level As Long) As String
    Indent = Space$(level * 2)
End Function

Private Function JoinPath(ByVal parentPath As String, ByVal childName As String) As String
    If Len(parentPath) = 0 Then
        JoinPath = childName
    Else
        JoinPath = parentPath & "/" & childName
    End If
End Function

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

Private Function LocalIsoTimestamp() As String
    LocalIsoTimestamp = Format$(Now, "yyyy-mm-dd\Thh:nn:ss")
End Function

Private Function DocumentTypeText(ByVal docType As Long) As String
    Select Case docType
        Case DOC_PART
            DocumentTypeText = "part"
        Case DOC_ASSEMBLY
            DocumentTypeText = "assembly"
        Case DOC_DRAWING
            DocumentTypeText = "drawing"
        Case Else
            DocumentTypeText = "unknown"
    End Select
End Function

Private Function ExternalReferenceStatusText(ByVal statusCode As Long) As String
    Select Case statusCode
        Case 0
            ExternalReferenceStatusText = "broken"
        Case 1
            ExternalReferenceStatusText = "locked"
        Case 3
            ExternalReferenceStatusText = "in_context"
        Case 4
            ExternalReferenceStatusText = "out_of_context"
        Case 5
            ExternalReferenceStatusText = "dangling"
        Case Else
            ExternalReferenceStatusText = "unknown"
    End Select
End Function

Private Function IsUsableArray(ByVal value As Variant) As Boolean
    On Error GoTo Fail
    If Not IsArray(value) Then Exit Function
    IsUsableArray = (UBound(value) >= LBound(value))
    Exit Function
Fail:
    IsUsableArray = False
End Function

Private Function ArrayStringAt(ByVal values As Variant, ByVal index As Long) As String
    On Error GoTo Fail
    If IsUsableArray(values) Then
        If index >= LBound(values) And index <= UBound(values) Then
            If Not IsNull(values(index)) And Not IsEmpty(values(index)) Then
                ArrayStringAt = CStr(values(index))
            End If
        End If
    End If
    Exit Function
Fail:
    ArrayStringAt = ""
End Function

Private Function ArrayLongAt(ByVal values As Variant, ByVal index As Long, _
                             ByVal fallback As Long) As Long
    On Error GoTo Fail
    If IsUsableArray(values) Then
        If index >= LBound(values) And index <= UBound(values) Then
            ArrayLongAt = CLng(values(index))
            Exit Function
        End If
    End If
Fail:
    ArrayLongAt = fallback
End Function

Private Function ArrayBooleanAt(ByVal values As Variant, ByVal index As Long) As Boolean
    On Error GoTo Fail
    If IsUsableArray(values) Then
        If index >= LBound(values) And index <= UBound(values) Then
            ArrayBooleanAt = CBool(values(index))
            Exit Function
        End If
    End If
Fail:
    ArrayBooleanAt = False
End Function
