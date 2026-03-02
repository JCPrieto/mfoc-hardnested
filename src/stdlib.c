/*-
 * Free/Libre Near Field Communication (NFC) library
 *
 * Libnfc historical contributors:
 * Copyright (C) 2009      Roel Verdult
 * Copyright (C) 2009-2013 Romuald Conty
 * Copyright (C) 2010-2012 Romain Tartière
 * Copyright (C) 2010-2013 Philippe Teuwen
 * Copyright (C) 2012-2013 Ludovic Rousseau
 * See AUTHORS file for a more comprehensive list of contributors.
 * Additional contributors of this file:
 * Copyright (C) 2013      Alex Lian
 *
 * This program is free software: you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as published by the
 * Free Software Foundation, either version 3 of the License, or (at your
 * option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 * FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
 * more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>
 *
 */

/**
 * @file stdlib.c
 * @brief Windows System compatibility
 */

// Handle platform specific includes
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>

// Windows does not provide POSIX setenv()/unsetenv(); map them to WinAPI.
int setenv(const char *name, const char *value, int overwrite)
{
  if (name == NULL || name[0] == '\0' || strchr(name, '=') != NULL || value == NULL) {
    errno = EINVAL;
    return -1;
  }

  if (!overwrite && getenv(name) != NULL) {
    return 0;
  }

  return SetEnvironmentVariableA(name, value) ? 0 : -1;
}

void unsetenv(const char *name)
{
  if (name == NULL || name[0] == '\0' || strchr(name, '=') != NULL) {
    return;
  }

  SetEnvironmentVariableA(name, NULL);
}
