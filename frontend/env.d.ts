/// <reference types="vite/client" />
// Module to support reading custom import.meta.env variables

interface ImportMetaEnv {
    readonly VITE_SERVER_URL: string
}

interface ImportMeta {
    readonly env: ImportMetaEnv
}