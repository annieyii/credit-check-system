"use client"

import { useState, useCallback } from "react"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Upload, FileJson, X } from "lucide-react"

export default function Dashboard() {
  const [studentType, setStudentType] = useState<"general" | "dual">("general")
  const [jsonData, setJsonData] = useState<string | null>(null)
  const [fileName, setFileName] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFile = useCallback((file: File) => {
    setError(null)
    
    if (!file.name.endsWith(".json")) {
      setError("請上傳 .json 格式的檔案")
      return
    }

    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const text = e.target?.result as string
        const parsed = JSON.parse(text)
        setJsonData(JSON.stringify(parsed, null, 2))
        setFileName(file.name)
      } catch {
        setError("無法解析 JSON 檔案，請確認檔案格式正確")
      }
    }
    reader.readAsText(file)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }, [handleFile])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
  }, [handleFile])

  const clearFile = useCallback(() => {
    setJsonData(null)
    setFileName(null)
    setError(null)
  }, [])

  return (
    <div className="min-h-screen bg-background p-6 md:p-10">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="text-2xl md:text-3xl font-bold text-foreground">
            畢業審判官
          </h1>
          <p className="text-muted-foreground">
            上傳學生資料 JSON 檔案進行畢業審查
          </p>
        </div>

        {/* Tabs */}
        <Tabs value={studentType} onValueChange={(v) => setStudentType(v as "general" | "dual")} className="w-full">
          <TabsList className="grid w-full grid-cols-2 max-w-md mx-auto">
            <TabsTrigger value="general" className="text-base">
              一般生
            </TabsTrigger>
            <TabsTrigger value="dual" className="text-base">
              雙輔生
            </TabsTrigger>
          </TabsList>
        </Tabs>

        {/* Upload Zone */}
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="text-lg flex items-center gap-2">
              <FileJson className="h-5 w-5 text-primary" />
              上傳 JSON 檔案
              {studentType === "general" ? " (一般生)" : " (雙輔生)"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              className={`
                relative border-2 border-dashed rounded-lg p-12 text-center
                transition-all duration-200 cursor-pointer
                ${isDragging 
                  ? "border-primary bg-primary/5" 
                  : "border-border hover:border-primary/50 hover:bg-muted/50"
                }
                ${error ? "border-destructive" : ""}
              `}
            >
              <input
                type="file"
                accept=".json"
                onChange={handleInputChange}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
              <div className="space-y-4">
                <div className={`
                  mx-auto w-16 h-16 rounded-full flex items-center justify-center
                  ${isDragging ? "bg-primary/10" : "bg-muted"}
                `}>
                  <Upload className={`h-8 w-8 ${isDragging ? "text-primary" : "text-muted-foreground"}`} />
                </div>
                <div>
                  <p className="text-foreground font-medium">
                    拖放檔案至此處，或點擊選擇檔案
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">
                    支援 .json 格式
                  </p>
                </div>
              </div>
            </div>
            
            {error && (
              <p className="text-sm text-destructive mt-3">{error}</p>
            )}
          </CardContent>
        </Card>

        {/* JSON Preview */}
        {jsonData && (
          <Card>
            <CardHeader className="pb-4">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2">
                  <FileJson className="h-5 w-5 text-accent" />
                  {fileName}
                </CardTitle>
                <button
                  onClick={clearFile}
                  className="p-2 rounded-md hover:bg-muted transition-colors"
                  aria-label="清除檔案"
                >
                  <X className="h-4 w-4 text-muted-foreground" />
                </button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="bg-muted rounded-lg p-4 max-h-96 overflow-auto">
                <pre className="text-sm font-mono text-foreground whitespace-pre-wrap break-all">
                  {jsonData}
                </pre>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
