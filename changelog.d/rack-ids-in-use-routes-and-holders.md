### Fixed
- A device placed in the rack no longer takes the id of a removed device that a
  cable's route still passes through, or that another device says it hangs on.
  Before, removing the device with the highest id could hand the same id to the
  next one placed, and the route then named the wrong device. Only the ids
  handed out change; the file format does not.
