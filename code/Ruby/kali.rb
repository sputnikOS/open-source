#!/usr/bin/env ruby
#
# kali_inventory.rb
#
# Generates a report of:
# - Kali version
# - Kernel information
# - CPU/RAM/Disk details
# - Network interfaces
# - Installed penetration-testing related packages
# - Available tool executables in common locations
#
# Usage:
#   ruby kali_inventory.rb
#

require 'open3'

def run(cmd)
  stdout, stderr, status = Open3.capture3(cmd)
  status.success? ? stdout.strip : "N/A"
rescue
  "N/A"
end

def section(title)
  puts "\n" + "=" * 80
  puts title
  puts "=" * 80
end

puts "\nKALI LINUX SYSTEM INVENTORY REPORT"
puts "Generated: #{Time.now}"

# ------------------------------------------------------------------
# OS INFORMATION
# ------------------------------------------------------------------
section("OPERATING SYSTEM")

puts "Hostname: #{run('hostname')}"
puts "Kernel:   #{run('uname -r')}"
puts "Arch:     #{run('uname -m')}"

if File.exist?('/etc/os-release')
  puts "\nOS Release:"
  puts File.read('/etc/os-release')
end

# ------------------------------------------------------------------
# CPU INFORMATION
# ------------------------------------------------------------------
section("CPU INFORMATION")

puts run("lscpu")

# ------------------------------------------------------------------
# MEMORY INFORMATION
# ------------------------------------------------------------------
section("MEMORY INFORMATION")

puts run("free -h")

# ------------------------------------------------------------------
# DISK INFORMATION
# ------------------------------------------------------------------
section("DISK INFORMATION")

puts run("df -h")

# ------------------------------------------------------------------
# NETWORK INFORMATION
# ------------------------------------------------------------------
section("NETWORK INTERFACES")

puts run("ip addr")

section("ROUTING TABLE")
puts run("ip route")

# ------------------------------------------------------------------
# PENETRATION TESTING PACKAGES
# ------------------------------------------------------------------
section("INSTALLED SECURITY / KALI PACKAGES")

patterns = [
  "nmap",
  "metasploit",
  "burp",
  "aircrack",
  "wireshark",
  "hashcat",
  "hydra",
  "john",
  "sqlmap",
  "nikto",
  "gobuster",
  "ffuf",
  "enum4linux",
  "bloodhound",
  "responder",
  "netexec",
  "crackmapexec",
  "impacket",
  "feroxbuster",
  "wfuzz",
  "seclists",
  "exploitdb",
  "searchsploit"
]

dpkg_list = run("dpkg -l")

patterns.each do |tool|
  matches = dpkg_list.lines.select { |line| line.downcase.include?(tool) }
  unless matches.empty?
    puts "\n--- #{tool.upcase} ---"
    matches.each { |m| puts m.chomp }
  end
end

# ------------------------------------------------------------------
# INSTALLED KALI META PACKAGES
# ------------------------------------------------------------------
section("KALI META PACKAGES")

puts run("dpkg -l | grep kali-")

# ------------------------------------------------------------------
# EXECUTABLE TOOL DISCOVERY
# ------------------------------------------------------------------
section("COMMON SECURITY TOOL EXECUTABLES")

executables = %w[
  nmap
  msfconsole
  burpsuite
  hashcat
  hydra
  john
  sqlmap
  nikto
  gobuster
  ffuf
  wireshark
  aircrack-ng
  tcpdump
  responder
  netexec
  crackmapexec
  bloodhound
  searchsploit
]

executables.each do |exe|
  path = run("which #{exe}")
  puts "#{exe.ljust(20)} #{path}" unless path == "N/A" || path.empty?
end

# ------------------------------------------------------------------
# ALL INSTALLED PACKAGES COUNT
# ------------------------------------------------------------------
section("PACKAGE STATISTICS")

package_count = run("dpkg -l | grep '^ii' | wc -l")
puts "Installed packages: #{package_count}"

# ------------------------------------------------------------------
# ACTIVE SERVICES
# ------------------------------------------------------------------
section("RUNNING SERVICES")

puts run("systemctl list-units --type=service --state=running --no-pager")

# ------------------------------------------------------------------
# OPEN LISTENING PORTS
# ------------------------------------------------------------------
section("LISTENING PORTS")

puts run("ss -tulpn")

puts "\nInventory completed."
