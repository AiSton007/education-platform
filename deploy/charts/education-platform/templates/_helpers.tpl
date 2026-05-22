{{/*
Common helpers for the education-platform chart.
*/}}

{{- define "ep.fullname" -}}
{{- printf "%s" .name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "ep.labels" -}}
app.kubernetes.io/name: {{ .name }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/managed-by: {{ .root.Release.Service }}
app.kubernetes.io/part-of: education-platform
{{- end -}}

{{- define "ep.selectorLabels" -}}
app.kubernetes.io/name: {{ .name }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
{{- end -}}

{{- define "ep.image" -}}
{{- $registry := .root.Values.global.imageRegistry -}}
{{- printf "%s/%s:%s" $registry .image.repository .image.tag -}}
{{- end -}}
