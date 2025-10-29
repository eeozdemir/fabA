{{- define "fastapi.name" -}}
{{ include "fastapi.chart" . }}
{{- end -}}

{{- define "fastapi.fullname" -}}
{{ printf "%s-%s" .Release.Name (include "fastapi.name" .) | trunc 63 | trimSuffix "-" }}
{{- end -}}

{{- define "fastapi.chart" -}}
{{ .Chart.Name }}
{{- end -}}