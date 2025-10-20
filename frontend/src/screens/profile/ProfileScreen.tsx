import React, { useState } from 'react';
import {
    View,
    Text,
    StyleSheet,
    ScrollView,
    Alert,
    TouchableOpacity,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import { Card, Button, Input } from '@/components/common';
import { useAuth, useUserRole } from '@/hooks';
import { lightTheme } from '@/styles/theme';

export const ProfileScreen: React.FC = () => {
    const navigation = useNavigation();
    const { user, logout, updateProfile, isLoading } = useAuth();
    const { role, isAdministrador } = useUserRole();

    const [isEditing, setIsEditing] = useState(false);
    const [editedUser, setEditedUser] = useState({
        firstName: user?.firstName || '',
        lastName: user?.lastName || '',
        email: user?.email || '',
        phoneNumber: user?.phoneNumber || '',
    });

    const handleLogout = async () => {
        Alert.alert(
            'Cerrar Sesión',
            '¿Está seguro que desea cerrar sesión?',
            [
                { text: 'Cancelar', style: 'cancel' },
                {
                    text: 'Cerrar Sesión',
                    style: 'destructive',
                    onPress: async () => {
                        await logout();
                    },
                },
            ]
        );
    };

    const handleChangePassword = () => {
        // Navigate to change password screen
        (navigation as any).navigate('ChangePassword');
    };

    const handleEditProfile = () => {
        setIsEditing(true);
    };

    const handleCancelEdit = () => {
        setIsEditing(false);
        setEditedUser({
            firstName: user?.firstName || '',
            lastName: user?.lastName || '',
            email: user?.email || '',
            phoneNumber: user?.phoneNumber || '',
        });
    };

    const handleSaveProfile = async () => {
        try {
            await updateProfile(editedUser);
            setIsEditing(false);
            Alert.alert('Éxito', 'Perfil actualizado correctamente');
        } catch (error) {
            Alert.alert('Error', 'No se pudo actualizar el perfil');
        }
    };

    return (
        <SafeAreaView style={styles.container} edges={['top', 'left', 'right']}>
            <ScrollView style={styles.scrollView} contentContainerStyle={styles.scrollContent}>
                <View style={styles.content}>
                    <Card
                        title="Información Personal"
                        style={styles.card}
                        actions={
                            !isEditing ? (
                                <TouchableOpacity onPress={handleEditProfile}>
                                    <Text style={styles.editText}>Editar</Text>
                                </TouchableOpacity>
                            ) : undefined
                        }
                    >
                        {isEditing ? (
                            <View style={styles.editForm}>
                                <Input
                                    label="Nombre"
                                    value={editedUser.firstName}
                                    onChangeText={(text) => setEditedUser(prev => ({ ...prev, firstName: text }))}
                                    placeholder="Ingrese su nombre"
                                />

                                <Input
                                    label="Apellido"
                                    value={editedUser.lastName}
                                    onChangeText={(text) => setEditedUser(prev => ({ ...prev, lastName: text }))}
                                    placeholder="Ingrese su apellido"
                                />

                                <Input
                                    label="Email"
                                    value={editedUser.email}
                                    onChangeText={(text) => setEditedUser(prev => ({ ...prev, email: text }))}
                                    placeholder="Ingrese su email"
                                    type="email"
                                />

                                <Input
                                    label="Teléfono"
                                    value={editedUser.phoneNumber}
                                    onChangeText={(text) => setEditedUser(prev => ({ ...prev, phoneNumber: text }))}
                                    placeholder="Ingrese su teléfono"
                                />

                                <View style={styles.editButtons}>
                                    <Button
                                        title="Cancelar"
                                        onPress={handleCancelEdit}
                                        variant="outline"
                                        style={styles.editButton}
                                        disabled={isLoading}
                                    />
                                    <Button
                                        title="Guardar"
                                        onPress={handleSaveProfile}
                                        style={styles.editButton}
                                        loading={isLoading}
                                    />
                                </View>
                            </View>
                        ) : (
                            <View>
                                <View style={styles.infoRow}>
                                    <Text style={styles.label}>Nombre:</Text>
                                    <Text style={styles.value}>
                                        {user?.firstName} {user?.lastName}
                                    </Text>
                                </View>
                                <View style={styles.infoRow}>
                                    <Text style={styles.label}>Email:</Text>
                                    <Text style={styles.value}>{user?.email}</Text>
                                </View>
                                <View style={styles.infoRow}>
                                    <Text style={styles.label}>Usuario:</Text>
                                    <Text style={styles.value}>{user?.username}</Text>
                                </View>
                                <View style={styles.infoRow}>
                                    <Text style={styles.label}>Teléfono:</Text>
                                    <Text style={styles.value}>{user?.phoneNumber || 'No especificado'}</Text>
                                </View>
                                <View style={styles.infoRow}>
                                    <Text style={styles.label}>Rol:</Text>
                                    <Text style={styles.value}>{user?.role.name}</Text>
                                </View>
                                <View style={styles.infoRow}>
                                    <Text style={styles.label}>Estado:</Text>
                                    <Text style={[styles.value, styles.activeStatus]}>
                                        {user?.isActive ? 'Activo' : 'Inactivo'}
                                    </Text>
                                </View>
                            </View>
                        )}
                    </Card>

                    <Card title="Seguridad" style={styles.card}>
                        <TouchableOpacity style={styles.securityOption} onPress={handleChangePassword}>
                            <Text style={styles.securityOptionText}>Cambiar Contraseña</Text>
                            <Text style={styles.securityOptionArrow}>›</Text>
                        </TouchableOpacity>
                    </Card>

                    <Card title="Permisos y Accesos" style={styles.card}>
                        <View style={styles.permissionsContainer}>
                            <Text style={styles.permissionTitle}>Módulos disponibles:</Text>
                            {user?.role.permissions.modules.map((module, index) => (
                                <Text key={index} style={styles.permissionItem}>
                                    • {module}
                                </Text>
                            ))}

                            <View style={styles.permissionRow}>
                                <Text style={styles.permissionLabel}>Crear registros:</Text>
                                <Text style={[styles.permissionValue, user?.role.permissions.canCreate && styles.permissionEnabled]}>
                                    {user?.role.permissions.canCreate ? 'Sí' : 'No'}
                                </Text>
                            </View>

                            <View style={styles.permissionRow}>
                                <Text style={styles.permissionLabel}>Generar reportes:</Text>
                                <Text style={[styles.permissionValue, user?.role.permissions.canGenerateReports && styles.permissionEnabled]}>
                                    {user?.role.permissions.canGenerateReports ? 'Sí' : 'No'}
                                </Text>
                            </View>
                        </View>
                    </Card>

                    <View style={styles.logoutContainer}>
                        <Button
                            title="Cerrar Sesión"
                            onPress={handleLogout}
                            variant="outline"
                            fullWidth
                        />
                    </View>
                </View>
            </ScrollView>
        </SafeAreaView>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: lightTheme.colors.surface,
    },
    scrollView: {
        flex: 1,
    },
    scrollContent: {
        paddingBottom: lightTheme.spacing.lg,
    },
    content: {
        padding: lightTheme.spacing.md,
    },
    card: {
        marginHorizontal: 0,
        marginBottom: lightTheme.spacing.md,
    },
    editText: {
        ...lightTheme.typography.body,
        color: lightTheme.colors.primary,
        fontWeight: '600',
    },
    editForm: {
        gap: lightTheme.spacing.md,
    },
    editButtons: {
        flexDirection: 'row',
        gap: lightTheme.spacing.md,
        marginTop: lightTheme.spacing.md,
    },
    editButton: {
        flex: 1,
    },
    infoRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: lightTheme.spacing.sm,
        borderBottomWidth: 1,
        borderBottomColor: lightTheme.colors.border,
    },
    label: {
        ...lightTheme.typography.body,
        fontWeight: '600',
        color: lightTheme.colors.text,
        flex: 1,
    },
    value: {
        ...lightTheme.typography.body,
        color: lightTheme.colors.textSecondary,
        flex: 2,
        textAlign: 'right',
    },
    activeStatus: {
        color: lightTheme.colors.success,
        fontWeight: '600',
    },
    securityOption: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: lightTheme.spacing.md,
        borderBottomWidth: 1,
        borderBottomColor: lightTheme.colors.border,
    },
    securityOptionText: {
        ...lightTheme.typography.body,
        color: lightTheme.colors.text,
    },
    securityOptionArrow: {
        ...lightTheme.typography.h3,
        color: lightTheme.colors.textSecondary,
    },
    permissionsContainer: {
        gap: lightTheme.spacing.sm,
    },
    permissionTitle: {
        ...lightTheme.typography.body,
        fontWeight: '600',
        color: lightTheme.colors.text,
        marginBottom: lightTheme.spacing.sm,
    },
    permissionItem: {
        ...lightTheme.typography.caption,
        color: lightTheme.colors.textSecondary,
        marginLeft: lightTheme.spacing.sm,
    },
    permissionRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: lightTheme.spacing.xs,
    },
    permissionLabel: {
        ...lightTheme.typography.caption,
        color: lightTheme.colors.text,
    },
    permissionValue: {
        ...lightTheme.typography.caption,
        color: lightTheme.colors.textSecondary,
    },
    permissionEnabled: {
        color: lightTheme.colors.success,
        fontWeight: '600',
    },
    logoutContainer: {
        marginTop: lightTheme.spacing.lg,
    },
});
