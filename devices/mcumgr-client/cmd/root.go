package cmd

import (
	"fmt"
	"os"
	"path"
	"rdfm-mcumgr-client/agent"
	"rdfm-mcumgr-client/appcfg"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

const appDir = "rdfm-mcumgr"

var verbose bool
var cfgFile string
var appCfg appcfg.AppConfig

var rootCmd = &cobra.Command{
	Use:   "rdfm-mcumgr-client",
	Short: "RDFM <-> mcumgr proxy client",

	Long: `A RDFM proxy client used for remotely updating devices
supporting the mcumgr protocol over BLE, serial and UDP over IP.`,

	// Main app entrypoint
	Run: func(cmd *cobra.Command, args []string) {
		err := viper.Unmarshal(&appCfg)
		cobra.CheckErr(err)

		agent.Run(appCfg, verbose)
	},
}

func Execute() {
	err := rootCmd.Execute()
	if err != nil {
		os.Exit(1)
	}
}

func init() {
	cobra.OnInitialize(initConfig)

	// Global flags
	gFlags := rootCmd.PersistentFlags()
	gFlags.StringVarP(&cfgFile, "config", "c", "", "Path to config file")
	gFlags.BoolVarP(&verbose, "verbose", "v", false, "Verbose (debug) logging")

	// Local command flags
	flags := rootCmd.Flags()
	flags.StringP("server", "s", "", "Full address for RDFM server")
	viper.BindPFlag("server", flags.Lookup("server"))

	flags.StringP("key-dir", "k", "", "Base path where device keys are stored")
	viper.BindPFlag("key_dir", flags.Lookup("key-dir"))

	flags.UintP("retries", "r", 0, "Retry count each update will be attempted before giving up")
	viper.BindPFlag("retries", flags.Lookup("retries"))

	flags.DurationP("interval", "i", 0, "Default interval between update checks")
	viper.BindPFlag("update_interval", flags.Lookup("interval"))
}

func initConfig() {
	if cfgFile != "" {
		// Use config file from the flag.
		viper.SetConfigFile(cfgFile)
	} else {
		// Find user config directory.
		homeCfg, err := os.UserConfigDir()
		cobra.CheckErr(err)

		// Config file sources: cwd, /home/user/.config, /etc
		viper.AddConfigPath(".")
		viper.AddConfigPath(path.Join(homeCfg, appDir))
		viper.AddConfigPath(path.Join("/etc", appDir))
		viper.SetConfigType("json")
		viper.SetConfigName("config")
	}

	viper.AutomaticEnv() // read in environment variables that match

	// If a config file is found, read it in.
	if err := viper.ReadInConfig(); err != nil {
		fmt.Fprintln(os.Stderr, "Failed to load in configuration")
		os.Exit(1)
	}
}
